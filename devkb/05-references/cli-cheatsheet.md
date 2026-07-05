---
title: CLI 명령어 치트시트
version: 1.0
---

# CLI 명령어 치트시트

## npm

```bash
npm init                    # 프로젝트 초기화
npm install                 # 의존성 설치
npm install --save-dev      # 개발 의존성 설치
npm list                    # 설치된 패키지 목록
npm outdated                # 업데이트 가능 패키지
npm update                  # 패키지 업데이트
npm uninstall package-name  # 패키지 제거
npm run build               # 빌드 스크립트 실행
npm test                    # 테스트 실행
```

## Prisma

```bash
npx prisma init             # Prisma 초기화
npx prisma generate         # Prisma Client 생성
npx prisma migrate dev --name migration_name  # 마이그레이션 생성
npx prisma migrate deploy   # 마이그레이션 적용
npx prisma db push          # 스키마 푸시
npx prisma db pull          # 스키마 당기기
npx prisma studio          # Prisma Studio 열기
npx prisma validate        # 스키마 검증
```

## Docker

```bash
docker build -t myapp:latest .     # 이미지 빌드
docker run -p 3000:3000 myapp      # 컨테이너 실행
docker ps                          # 실행 중인 컨테이너
docker logs container-id           # 로그 확인
docker exec -it container-id bash  # 컨테이너 접속
docker stop container-id           # 컨테이너 중지
docker rm container-id             # 컨테이너 제거
docker images                      # 이미지 목록
docker rmi image-id                # 이미지 제거
```

## Kubernetes

```bash
kubectl apply -f deployment.yaml    # 리소스 생성
kubectl get pods                    # Pod 목록
kubectl describe pod pod-name       # Pod 정보
kubectl logs pod-name               # Pod 로그
kubectl exec -it pod-name -- bash   # Pod 접속
kubectl scale deployment myapp --replicas=3  # 스케일 조정
kubectl rollout status deployment/myapp      # 배포 상태
kubectl delete pod pod-name         # Pod 제거
kubectl get all                     # 모든 리소스
```

## git

```bash
git clone repo-url                  # 저장소 복제
git status                          # 상태 확인
git add .                           # 변경사항 스테이징
git commit -m "message"             # 커밋
git push                            # 푸시
git pull                            # 풀
git branch                          # 브랜치 목록
git checkout -b branch-name         # 브랜치 생성
git merge branch-name               # 브랜치 병합
git log                             # 커밋 로그
```

## curl

```bash
curl https://example.com                      # GET 요청
curl -X POST https://example.com -d data      # POST 요청
curl -H "Authorization: Bearer token" url     # 헤더 추가
curl -X PUT https://example.com -d data       # PUT 요청
curl -X DELETE https://example.com            # DELETE 요청
curl -i https://example.com                   # 응답 헤더 표시
curl -v https://example.com                   # 상세 정보
```

