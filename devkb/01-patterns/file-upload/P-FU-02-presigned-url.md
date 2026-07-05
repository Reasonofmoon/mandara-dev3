---
id: P-FU-02
title: Presigned URL 패턴
stage: Implement
layer: API
pattern_family: Persistence
tech_tags: [S3, Presigned URL, 직접 업로드, 서버 부하 절감]
linked_errors: [E-FU-03, E-FU-04]
linked_flows: [F-FU-02]
linked_prompts: [PR-FU-02]
---

# Presigned URL 패턴

## 목표
AWS S3 presigned URL을 활용하여 클라이언트가 서버를 거치지 않고 직접 파일을 업로드하여 서버 부하를 줄입니다.

## 언제 사용하는가
- 서버 부하를 최소화해야 할 때
- 클라이언트가 직접 클라우드 스토리지에 접근해야 할 때
- 임시 접근 권한이 필요한 경우
- 대규모 동시 업로드

## 핵심 구조

### 서버 - Presigned URL 생성

```typescript
// upload/upload.service.ts
import {
  S3Client,
  PutObjectCommand,
} from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import { Injectable } from '@nestjs/common';

interface PresignedUrlRequest {
  fileName: string;
  fileType: string;
  fileSize: number;
}

interface PresignedUrlResponse {
  uploadUrl: string;
  fileKey: string;
  expiresIn: number;
}

@Injectable()
export class S3UploadService {
  private s3Client: S3Client;
  private readonly bucket = process.env.AWS_S3_BUCKET;
  private readonly region = process.env.AWS_REGION;

  constructor() {
    this.s3Client = new S3Client({ region: this.region });
  }

  async generatePresignedUrl(
    request: PresignedUrlRequest,
  ): Promise<PresignedUrlResponse> {
    // 파일 키 생성 (예: uploads/user-123/2024-01-01-filename.ext)
    const userId = 'user-123'; // 실제로는 요청 사용자에서 추출
    const timestamp = new Date().toISOString().split('T')[0];
    const fileKey = `uploads/${userId}/${timestamp}-${request.fileName}`;

    // 파일 크기 검증 (예: 100MB 제한)
    const MAX_FILE_SIZE = 100 * 1024 * 1024;
    if (request.fileSize > MAX_FILE_SIZE) {
      throw new BadRequestException(
        `File size exceeds ${MAX_FILE_SIZE / 1024 / 1024}MB limit`
      );
    }

    // 허용된 파일 타입 검증
    const allowedTypes = [
      'image/jpeg',
      'image/png',
      'image/gif',
      'application/pdf',
      'video/mp4',
    ];

    if (!allowedTypes.includes(request.fileType)) {
      throw new BadRequestException('File type not allowed');
    }

    const command = new PutObjectCommand({
      Bucket: this.bucket,
      Key: fileKey,
      ContentType: request.fileType,
      ContentLength: request.fileSize,
      // 서버에서만 업로드 가능하도록 메타데이터 추가
      Metadata: {
        uploadedAt: new Date().toISOString(),
        uploadedBy: userId,
      },
      // CORS를 위해 필요한 헤더
      ACL: 'private',
    });

    const expiresIn = 3600; // 1시간
    const uploadUrl = await getSignedUrl(this.s3Client, command, {
      expiresIn,
    });

    return {
      uploadUrl,
      fileKey,
      expiresIn,
    };
  }

  // 업로드 확인 (S3의 파일 존재 여부)
  async confirmUpload(fileKey: string): Promise<boolean> {
    try {
      const command = new HeadObjectCommand({
        Bucket: this.bucket,
        Key: fileKey,
      });

      await this.s3Client.send(command);
      return true;
    } catch (error) {
      return false;
    }
  }

  // 파일 URL 생성 (다운로드/조회용)
  async getFileUrl(fileKey: string): Promise<string> {
    const command = new GetObjectCommand({
      Bucket: this.bucket,
      Key: fileKey,
    });

    const expiresIn = 86400; // 24시간
    return getSignedUrl(this.s3Client, command, { expiresIn });
  }
}

// upload/upload.controller.ts
@Controller('api/uploads')
export class UploadController {
  constructor(private uploadService: S3UploadService) {}

  @Post('presigned-url')
  @UseGuards(JwtGuard)
  async getPresignedUrl(
    @Body() request: PresignedUrlRequest,
  ): Promise<PresignedUrlResponse> {
    return this.uploadService.generatePresignedUrl(request);
  }

  @Post('confirm')
  @UseGuards(JwtGuard)
  async confirmUpload(
    @Body() { fileKey }: { fileKey: string },
  ) {
    const exists = await this.uploadService.confirmUpload(fileKey);

    if (!exists) {
      throw new BadRequestException('File not found in storage');
    }

    // 데이터베이스에 파일 기록
    await this.prisma.file.create({
      data: {
        key: fileKey,
        userId: request.user.id,
        size: request.fileSize,
        type: request.fileType,
      },
    });

    return { success: true };
  }
}
```

### 클라이언트

```typescript
// upload/s3-uploader.ts
interface PresignedUrlRequest {
  fileName: string;
  fileType: string;
  fileSize: number;
}

interface UploadProgress {
  percentage: number;
  bytesUploaded: number;
  bytesTotal: number;
}

export class S3Uploader {
  private readonly API_BASE = process.env.REACT_APP_API_URL;

  async uploadFile(
    file: File,
    onProgress?: (progress: UploadProgress) => void,
  ): Promise<string> {
    // 1. Presigned URL 요청
    const presignedResponse = await fetch(
      `${this.API_BASE}/api/uploads/presigned-url`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fileName: file.name,
          fileType: file.type,
          fileSize: file.size,
        }),
        credentials: 'include',
      },
    );

    if (!presignedResponse.ok) {
      throw new Error('Failed to get presigned URL');
    }

    const { uploadUrl, fileKey } = await presignedResponse.json();

    // 2. 직접 S3에 업로드
    const xhr = new XMLHttpRequest();

    // 진행률 추적
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        const percentComplete = (e.loaded / e.total) * 100;
        onProgress({
          percentage: percentComplete,
          bytesUploaded: e.loaded,
          bytesTotal: e.total,
        });
      }
    });

    // 오류 처리
    xhr.addEventListener('error', () => {
      throw new Error('Upload failed');
    });

    // 업로드 수행
    await new Promise((resolve, reject) => {
      xhr.onload = () => {
        if (xhr.status === 200) {
          resolve(null);
        } else {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      };
      xhr.onerror = () => reject(new Error('Upload error'));

      xhr.open('PUT', uploadUrl);
      xhr.setRequestHeader('Content-Type', file.type);
      xhr.send(file);
    });

    // 3. 서버에 업로드 확인
    await fetch(`${this.API_BASE}/api/uploads/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fileKey }),
      credentials: 'include',
    });

    return fileKey;
  }
}
```

### React 컴포넌트

```typescript
// components/s3-file-upload.tsx
import { useState } from 'react';
import { S3Uploader, UploadProgress } from 'upload/s3-uploader';

export function S3FileUpload() {
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [status, setStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>(
    'idle'
  );
  const [error, setError] = useState<string | null>(null);

  const uploader = new S3Uploader();

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setStatus('uploading');
    setProgress(null);
    setError(null);

    try {
      const fileKey = await uploader.uploadFile(file, setProgress);
      setStatus('success');
      console.log('Uploaded:', fileKey);
    } catch (err) {
      setStatus('error');
      setError((err as Error).message);
    }
  };

  return (
    <div className="s3-upload">
      <input
        type="file"
        onChange={handleFileSelect}
        disabled={status === 'uploading'}
      />

      {progress && (
        <div className="progress">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${progress.percentage}%` }}
            />
          </div>
          <p>{Math.round(progress.percentage)}%</p>
          <p>
            {Math.round(progress.bytesUploaded / 1024 / 1024)} /{' '}
            {Math.round(progress.bytesTotal / 1024 / 1024)} MB
          </p>
        </div>
      )}

      {status === 'success' && <p className="success">업로드 완료!</p>}
      {error && <p className="error">오류: {error}</p>}
    </div>
  );
}
```

## 최소 예제

```typescript
// 서버
const url = await getSignedUrl(s3, new PutObjectCommand({
  Bucket: 'my-bucket',
  Key: 'file.txt',
}), { expiresIn: 3600 });

// 클라이언트
const response = await fetch(presignedUrl, {
  method: 'PUT',
  body: file,
  headers: { 'Content-Type': file.type },
});
```

## CORS 설정

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
    "AllowedOrigins": ["https://yourdomain.com"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3000
  }
]
```

## 보안 고려사항

```typescript
// 1. 파일 크기 제한
if (fileSize > 100 * 1024 * 1024) { // 100MB
  throw new Error('File too large');
}

// 2. 파일 타입 검증
const allowedTypes = ['image/jpeg', 'image/png', 'application/pdf'];
if (!allowedTypes.includes(fileType)) {
  throw new Error('File type not allowed');
}

// 3. 사용자별 폴더 격리
const fileKey = `uploads/${userId}/${fileName}`;

// 4. 임시 파일 정리
// 24시간 후 사용되지 않은 파일 삭제
```

## 안티패턴

### 1. S3 액세스 키를 클라이언트에 노출

```typescript
// ❌ 나쁜 예제
const s3 = new S3Client({
  credentials: {
    accessKeyId: AWS_ACCESS_KEY, // 클라이언트에 노출!
    secretAccessKey: AWS_SECRET_KEY,
  },
});

// ✅ 좋은 예제
// 서버에서만 presigned URL 생성
const uploadUrl = await getSignedUrl(s3Client, command);
// 클라이언트는 임시 URL만 받음
```

### 2. 파일 검증 누락

```typescript
// ❌ 나쁜 예제
uploadFile(file) {
  return fetch(presignedUrl, {
    method: 'PUT',
    body: file, // 검증 없음!
  });
}

// ✅ 좋은 예제
uploadFile(file) {
  if (file.size > MAX_SIZE) throw new Error('Too large');
  if (!ALLOWED_TYPES.includes(file.type)) throw new Error('Invalid type');

  return fetch(presignedUrl, {
    method: 'PUT',
    body: file,
  });
}
```

## 연결된 오류

- **E-FU-03**: Presigned URL 만료로 인한 업로드 실패
- **E-FU-04**: 파일 검증 누락으로 인한 보안 위협

## 연결된 플로우

- **F-FU-02**: 프로필 이미지 업로드

## 참고 자료

- AWS S3 Presigned URLs: https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html
- AWS SDK for JavaScript v3: https://docs.aws.amazon.com/sdk-for-javascript/v3/
