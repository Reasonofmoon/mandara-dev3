---
title: Node.js와 NestJS 참조 가이드
version: 1.0
---

# Node.js와 NestJS 참조 가이드

NestJS 모듈, Guard, Pipe, Express 미들웨어 참조입니다.

## NestJS 핵심 개념

### Module 구조

```typescript
@Module({
  controllers: [UsersController],
  providers: [UsersService],
  exports: [UsersService],  // 다른 모듈에서 사용 가능
  imports: [DatabaseModule]  // 의존성
})
export class UsersModule {}
```

### Controller

```typescript
@Controller('users')
export class UsersController {
  @Get()
  findAll() {}

  @Get(':id')
  findOne(@Param('id') id: string) {}

  @Post()
  create(@Body() createUserDto: CreateUserDto) {}

  @Put(':id')
  update(@Param('id') id: string, @Body() updateUserDto: UpdateUserDto) {}

  @Delete(':id')
  remove(@Param('id') id: string) {}
}
```

### Service

```typescript
@Injectable()
export class UsersService {
  constructor(
    @InjectRepository(User)
    private usersRepository: Repository<User>,
  ) {}

  findAll() {
    return this.usersRepository.find();
  }

  findOne(id: number) {
    return this.usersRepository.findOne({ where: { id } });
  }

  create(createUserDto: CreateUserDto) {
    return this.usersRepository.save(createUserDto);
  }
}
```

## Guard와 Middleware

### Guard

```typescript
@Injectable()
export class AuthGuard implements CanActivate {
  constructor(private jwtService: JwtService) {}

  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest();
    const token = request.headers.authorization?.split(' ')[1];

    try {
      const payload = this.jwtService.verify(token);
      request.user = payload;
      return true;
    } catch {
      return false;
    }
  }
}

// 사용
@UseGuards(AuthGuard)
@Get('protected')
getProtected() {}
```

### RoleGuard

```typescript
@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const requiredRoles = this.reflector.get<string[]>(
      'roles',
      context.getHandler(),
    );

    if (!requiredRoles) {
      return true;
    }

    const request = context.switchToHttp().getRequest();
    const user = request.user;

    return requiredRoles.some(role => user.roles?.includes(role));
  }
}

// 데코레이터
export const Roles = (...roles: string[]) =>
  SetMetadata('roles', roles);

// 사용
@UseGuards(AuthGuard, RolesGuard)
@Roles('admin')
@Get('admin')
getAdmin() {}
```

## Pipe

### ValidationPipe

```typescript
import { ValidationPipe } from '@nestjs/common';

// main.ts
async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.useGlobalPipes(new ValidationPipe({
    whitelist: true,          // 정의되지 않은 필드 제거
    forbidNonWhitelisted: true, // 정의되지 않은 필드 시 에러
    transform: true,          // 타입 변환
    transformOptions: {
      enableImplicitConversion: true
    }
  }));
  await app.listen(3000);
}
```

### 커스텀 Pipe

```typescript
@Injectable()
export class ParseIntPipe implements PipeTransform {
  transform(value: string): number {
    const val = parseInt(value, 10);
    if (isNaN(val)) {
      throw new BadRequestException('Validation failed');
    }
    return val;
  }
}

// 사용
@Get(':id')
findOne(@Param('id', ParseIntPipe) id: number) {}
```

## Express 미들웨어

### 미들웨어 생성

```typescript
@Injectable()
export class LoggerMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction) {
    console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
    next();
  }
}

// 적용
@Module({})
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer) {
    consumer
      .apply(LoggerMiddleware)
      .forRoutes('*');  // 모든 경로
  }
}

// 또는 특정 경로만
.forRoutes({ path: 'users', method: RequestMethod.GET });
```

### 함수형 미들웨어

```typescript
export function logger(req: Request, res: Response, next: NextFunction) {
  console.log(`Request...`);
  next();
}

// 적용
app.use(logger);
```

## 예외 처리

```typescript
@Catch(HttpException)
export class HttpExceptionFilter implements ExceptionFilter {
  catch(exception: HttpException, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();
    const status = exception.getStatus();

    response.status(status).json({
      statusCode: status,
      timestamp: new Date().toISOString(),
      path: request.url,
      message: exception.message,
    });
  }
}

// 적용
@UseFilters(HttpExceptionFilter)
@Get()
findAll() {}
```

## 데이터베이스 연결

### TypeORM 설정

```typescript
@Module({
  imports: [
    TypeOrmModule.forRoot({
      type: 'postgres',
      host: process.env.DATABASE_HOST,
      port: parseInt(process.env.DATABASE_PORT),
      username: process.env.DATABASE_USER,
      password: process.env.DATABASE_PASSWORD,
      database: process.env.DATABASE_NAME,
      entities: [__dirname + '/../**/*.entity{.ts,.js}'],
      synchronize: false,  // 프로덕션에서는 false
      migrations: [__dirname + '/../migrations/*{.ts,.js}'],
      migrationsRun: true
    })
  ]
})
export class DatabaseModule {}
```

### Entity

```typescript
@Entity('users')
export class User {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ type: 'varchar', length: 255, unique: true })
  email: string;

  @Column({ type: 'varchar', length: 255 })
  name: string;

  @Column({ type: 'timestamp', default: () => 'CURRENT_TIMESTAMP' })
  createdAt: Date;

  @ManyToOne(() => Role, role => role.users)
  role: Role;

  @OneToMany(() => Post, post => post.author)
  posts: Post[];
}
```

## Decorator 모음

| Decorator | 용도 |
|-----------|------|
| `@Module` | 모듈 정의 |
| `@Controller` | 컨트롤러 정의 |
| `@Injectable` | 서비스/프로바이더 정의 |
| `@Get`, `@Post`, `@Put` | HTTP 메서드 |
| `@Param`, `@Query`, `@Body` | 요청 데이터 추출 |
| `@UseGuards` | 가드 적용 |
| `@UseFilters` | 예외 필터 적용 |
| `@UseInterceptors` | 인터셉터 적용 |
| `@Inject` | 의존성 주입 |
| `@Optional` | 선택적 의존성 |
