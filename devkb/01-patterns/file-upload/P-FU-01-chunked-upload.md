---
id: P-FU-01
title: 청크 업로드 패턴
stage: Implement
layer: UI
pattern_family: Persistence
tech_tags: [대용량 파일, 청킹, 재개 가능 업로드, 진행률]
linked_errors: [E-FU-01, E-FU-02]
linked_flows: [F-FU-01]
linked_prompts: [PR-FU-01]
---

# 청크 업로드 패턴

## 목표
대용량 파일을 작은 청크로 나누어 업로드하고, 실패 시 재개 가능하게 만들어 사용자 경험을 개선합니다.

## 언제 사용하는가
- 대용량 파일 업로드 (수백 MB 이상)
- 네트워크가 불안정한 환경
- 업로드 진행률 표시가 필요한 경우
- 실패 후 재개 기능이 필요한 경우

## 핵심 구조

### 클라이언트

```typescript
// upload/chunk-uploader.ts
interface ChunkUploadOptions {
  chunkSize?: number; // 청크 크기 (기본값: 5MB)
  maxRetries?: number; // 재시도 횟수
  onProgress?: (progress: UploadProgress) => void;
  onComplete?: () => void;
  onError?: (error: Error) => void;
}

interface UploadProgress {
  uploadId: string;
  totalChunks: number;
  completedChunks: number;
  percentage: number;
  bytesUploaded: number;
  bytesTotal: number;
}

export class ChunkUploader {
  private readonly DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024; // 5MB
  private readonly DEFAULT_MAX_RETRIES = 3;

  async uploadFile(
    file: File,
    uploadUrl: string,
    options: ChunkUploadOptions = {},
  ): Promise<string> {
    const chunkSize = options.chunkSize || this.DEFAULT_CHUNK_SIZE;
    const maxRetries = options.maxRetries || this.DEFAULT_MAX_RETRIES;
    const totalChunks = Math.ceil(file.size / chunkSize);

    // 고유한 업로드 ID 생성
    const uploadId = this.generateUploadId(file);

    // 업로드된 청크 확인 (재개)
    const uploadedChunks = await this.getUploadedChunks(uploadId);

    let completedChunks = uploadedChunks.length;
    let bytesUploaded = completedChunks * chunkSize;

    // 이미 업로드된 부분 스킵
    for (let i = 0; i < totalChunks; i++) {
      if (uploadedChunks.includes(i)) {
        continue;
      }

      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, file.size);
      const chunk = file.slice(start, end);

      try {
        await this.uploadChunk(
          chunk,
          uploadUrl,
          uploadId,
          i,
          totalChunks,
          maxRetries,
        );

        completedChunks++;
        bytesUploaded = completedChunks * chunkSize;

        // 진행률 업데이트
        if (options.onProgress) {
          options.onProgress({
            uploadId,
            totalChunks,
            completedChunks,
            percentage: (completedChunks / totalChunks) * 100,
            bytesUploaded,
            bytesTotal: file.size,
          });
        }
      } catch (error) {
        if (options.onError) {
          options.onError(error as Error);
        }
        throw error;
      }
    }

    // 업로드 완료
    if (options.onComplete) {
      options.onComplete();
    }

    return uploadId;
  }

  private async uploadChunk(
    chunk: Blob,
    uploadUrl: string,
    uploadId: string,
    chunkIndex: number,
    totalChunks: number,
    maxRetries: number,
  ): Promise<void> {
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const formData = new FormData();
        formData.append('file', chunk);
        formData.append('uploadId', uploadId);
        formData.append('chunkIndex', String(chunkIndex));
        formData.append('totalChunks', String(totalChunks));

        const response = await fetch(uploadUrl, {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`Upload chunk failed: ${response.statusText}`);
        }

        return;
      } catch (error) {
        if (attempt === maxRetries) {
          throw error;
        }

        // 지수 백오프
        const delay = 1000 * Math.pow(2, attempt);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  private async getUploadedChunks(uploadId: string): Promise<number[]> {
    try {
      const response = await fetch(`/api/uploads/${uploadId}/status`);
      if (response.ok) {
        const data = await response.json();
        return data.uploadedChunks || [];
      }
    } catch (error) {
      // 무시
    }
    return [];
  }

  private generateUploadId(file: File): string {
    return `${file.name}-${file.size}-${Date.now()}`;
  }
}
```

### React 컴포넌트

```typescript
// components/file-upload.tsx
import { useState } from 'react';
import { ChunkUploader, UploadProgress } from 'upload/chunk-uploader';

export function FileUploadComponent() {
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [status, setStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  const uploader = new ChunkUploader();

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setStatus('uploading');
    setError(null);

    try {
      await uploader.uploadFile(file, '/api/upload', {
        chunkSize: 5 * 1024 * 1024, // 5MB
        onProgress: setProgress,
        onComplete: () => setStatus('success'),
        onError: (err) => {
          setStatus('error');
          setError(err.message);
        },
      });
    } catch (err) {
      setStatus('error');
      setError((err as Error).message);
    }
  };

  return (
    <div className="upload-container">
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
          <p>
            {progress.completedChunks} / {progress.totalChunks} 청크
            ({Math.round(progress.percentage)}%)
          </p>
          <p>
            {Math.round(progress.bytesUploaded / 1024 / 1024)} MB /{' '}
            {Math.round(progress.bytesTotal / 1024 / 1024)} MB
          </p>
        </div>
      )}

      {status === 'success' && <p className="success">업로드 완료!</p>}
      {status === 'error' && <p className="error">{error}</p>}
    </div>
  );
}
```

### 서버 (NestJS)

```typescript
// upload/upload.controller.ts
import {
  Controller,
  Post,
  Body,
  UseInterceptors,
  UploadedFile,
  Param,
  Get,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { UploadService } from './upload.service';

@Controller('api/upload')
export class UploadController {
  constructor(private uploadService: UploadService) {}

  @Post()
  @UseInterceptors(FileInterceptor('file'))
  async uploadChunk(
    @UploadedFile() file: Express.Multer.File,
    @Body('uploadId') uploadId: string,
    @Body('chunkIndex') chunkIndex: string,
    @Body('totalChunks') totalChunks: string,
  ) {
    const index = parseInt(chunkIndex, 10);
    const total = parseInt(totalChunks, 10);

    await this.uploadService.saveChunk(
      uploadId,
      index,
      total,
      file.buffer,
    );

    return { success: true };
  }

  @Get(':uploadId/status')
  async getUploadStatus(@Param('uploadId') uploadId: string) {
    const uploadedChunks = await this.uploadService.getUploadedChunks(
      uploadId,
    );
    return { uploadedChunks };
  }
}

// upload/upload.service.ts
@Injectable()
export class UploadService {
  constructor(private prisma: PrismaService) {}

  async saveChunk(
    uploadId: string,
    chunkIndex: number,
    totalChunks: number,
    buffer: Buffer,
  ) {
    const uploadDir = `uploads/temp/${uploadId}`;
    const chunkPath = `${uploadDir}/chunk-${chunkIndex}`;

    // 디렉토리 생성
    await fs.promises.mkdir(uploadDir, { recursive: true });

    // 청크 저장
    await fs.promises.writeFile(chunkPath, buffer);

    // 진행 상태 저장
    await this.prisma.uploadProgress.upsert({
      where: { uploadId },
      create: {
        uploadId,
        totalChunks,
        uploadedChunks: [chunkIndex],
      },
      update: {
        uploadedChunks: {
          push: chunkIndex,
        },
        updatedAt: new Date(),
      },
    });

    // 모든 청크가 업로드되면 파일 합치기
    const progress = await this.prisma.uploadProgress.findUnique({
      where: { uploadId },
    });

    if (progress && progress.uploadedChunks.length === totalChunks) {
      await this.assembleChunks(uploadId, totalChunks);
    }
  }

  private async assembleChunks(
    uploadId: string,
    totalChunks: number,
  ) {
    const uploadDir = `uploads/temp/${uploadId}`;
    const finalPath = `uploads/final/${uploadId}`;

    // 최종 파일 생성
    const writeStream = fs.createWriteStream(finalPath);

    for (let i = 0; i < totalChunks; i++) {
      const chunkPath = `${uploadDir}/chunk-${i}`;
      const chunk = await fs.promises.readFile(chunkPath);
      writeStream.write(chunk);
    }

    writeStream.end();

    // 임시 파일 정리
    await fs.promises.rm(uploadDir, { recursive: true });
  }

  async getUploadedChunks(uploadId: string): Promise<number[]> {
    const progress = await this.prisma.uploadProgress.findUnique({
      where: { uploadId },
    });

    return progress?.uploadedChunks || [];
  }
}
```

## 최소 예제

```typescript
async function uploadFile(file: File) {
  const chunkSize = 1024 * 1024; // 1MB
  const chunks = Math.ceil(file.size / chunkSize);

  for (let i = 0; i < chunks; i++) {
    const start = i * chunkSize;
    const end = Math.min(start + chunkSize, file.size);
    const chunk = file.slice(start, end);

    const formData = new FormData();
    formData.append('file', chunk);
    formData.append('chunkIndex', String(i));

    await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });
  }
}
```

## 안티패턴

### 1. 재개 기능 없이 청킹

```typescript
// ❌ 나쁜 예제 - 실패하면 처음부터 다시 업로드
for (let i = 0; i < chunks; i++) {
  await uploadChunk(i); // 중간에 실패하면 이전 청크들 낭비
}

// ✅ 좋은 예제
const uploaded = await getUploadedChunks(uploadId);
for (let i = 0; i < chunks; i++) {
  if (uploaded.includes(i)) continue; // 이미 업로드된 부분 스킵
  await uploadChunk(i);
}
```

## 연결된 오류

- **E-FU-01**: 청크 업로드 실패로 인한 재시도 필요
- **E-FU-02**: 업로드 중단 후 재개 실패

## 연결된 플로우

- **F-FU-01**: 대용량 파일 업로드 플로우

## 참고 자료

- MDN File API: https://developer.mozilla.org/en-US/docs/Web/API/File
- AWS Multipart Upload: https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html
