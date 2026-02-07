# MY-SCHEDULER-APP-CDK

HTML / CSS / JavaScript を用いたフロントエンドと、Python 製のバックエンド API で構成した、シンプルなスケジュール管理 Web アプリケーションです。

フロントエンドは S3、バックエンドは Lambda と API Gateway、データベースは RDS（MySQL）を利用したサーバーレスアーキテクチャで構築しています。また、CloudFront を用いて独自ドメインおよび TLS 証明書を適用しています。

CloudFront を除く部分は、AWS CDK（Python）を使用して自動的にデプロイ可能です（my_schedule_app_cdk/my_schedule_app_cdk_stack.py）。

## 概要

このプロジェクトは、以下のAWSサービスを利用した Web アプリケーションシステムです。

- **API Gateway** - RESTful APIエンドポイント
- **Lambda** - バックエンド処理（イベント管理、認証）
- **RDS (MySQL)** - スケジュールデータベース
- **S3** - フロントエンド（HTML）のホスティング、およびバッチ処理用データ（CSV）の格納
- **Cognito** - ユーザー認証
- **VPC** - ネットワーク（Lambda / RDS をプライベートサブネットに配置し、Lambda は VPC エンドポイント経由で各 AWS サービスに接続）
- **KMS** - 暗号化キー管理
- **Secrets Manager** - RDS認証情報の管理
- **CloudFront** - 独自ドメインおよびTLS証明書適用

## Web サイトの利用方法

- URL  
  https://my-schedule-app.takafukuz.dev/

- デモ用ログイン情報  
  - ユーザー名：demouser01  
  - パスワード：Demouser#2026

  - ユーザー名：demouser02  
  - パスワード：Demouser#2026

  - ユーザー名：demouser03  
  - パスワード：Demouser#2026

※ご自由にご操作いただけますが、個人情報や機密情報は登録しないようご注意ください。

## インフラ構成

- 「my-schedule-app_インフラ構成図.png」を参照

## アーキテクチャ概要

- 「my-schedule-app_アーキテクチャ概要図.png」を参照

## プロジェクト構成

```
my-schedule-app-cdk/
├── app.py                          # CDKアプリケーションエントリーポイント
├── cdk.json                        # CDK設定ファイル
├── requirements.txt                # Python依存パッケージ
├── data/
│   └── holiday-data.csv            # 祝日データ（S3にアップロード）
├── src/
│   ├── backend/
│   │   ├── functions/              # Lambda関数
│   │   │   ├── add_event/          # イベント追加
│   │   │   ├── delete_event/       # イベント削除
│   │   │   ├── get_calendar/       # カレンダー取得
│   │   │   ├── get_detail/         # イベント詳細取得
│   │   │   ├── get_event/          # イベント取得
│   │   │   ├── init_db/            # データベース初期化
│   │   │   └── update_event/       # イベント更新
│   │   ├── layer/                  # Lambda Layer（共有モジュール）
│   │   │   ├── logging_utils.py
│   │   │   ├── secret_utils.py
│   │   │   ├── ssm_utils.py
│   │   │   └── user_utils.py
│   │   └── layer2/                 # Lambda Layer（pymysql）
│   │       └── pymysql/
│   └── frontend/                   # Webフロントエンド
│       ├── index.html
│       ├── add-event.html
│       ├── edit-event.html
│       ├── get-calendar.html
│       ├── get-detail.html
│       ├── change-password.html
│       ├── change-initial-password.html
│       ├── css/
│       │   └── style.css
│       └── js/
│           ├── auth/               # 認証関連
│           │   ├── login.js
│           │   ├── logout.js
│           │   ├── is-logged-in.js
│           │   ├── change-password.js
│           │   ├── change-initial-password.js
│           │   └── refresh-cognito-token.js
│           ├── calendar/           # カレンダー操作
│           │   ├── add-event.js
│           │   ├── edit-event.js
│           │   ├── get-calendar.js
│           │   └── get-detail.js
│           └── config/             # 設定
│               ├── api-gateway-config.js
│               └── cognito-config.js
├── my_schedule_app_cdk/
│   ├── __init__.py
│   └── my_schedule_app_cdk_stack.py # CDKスタック定義
└── tests/
    └── unit/
        └── test_my_schedule_app_cdk_stack.py
```

## 前提条件

- Python 3.9以上
- AWS CDK CLI
- AWS アカウント
- AWS認証情報の設定

## セットアップ手順

### 1. 仮想環境の作成

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate.bat

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 3. 開発環境のセットアップ（オプション）

```bash
pip install -r requirements-dev.txt
```

## CDK コマンド

### スタック一覧の表示

```bash
cdk ls
```

### CloudFormation テンプレートの生成

```bash
cdk synth
```

### スタックのデプロイ

```bash
cdk deploy
```

### スタックの差分確認

```bash
cdk diff
```

### ドキュメントの表示

```bash
cdk docs
```

### デプロイの削除

```bash
cdk destroy
```

## バックエンド機能

### Lambda関数一覧

| 関数名 | パス | 説明 |
|--------|------|------|
| add_event | `src/backend/functions/add_event/` | 新しいスケジュール/イベントを追加 |
| delete_event | `src/backend/functions/delete_event/` | スケジュール/イベントを削除 |
| get_calendar | `src/backend/functions/get_calendar/` | カレンダー情報を取得 |
| get_detail | `src/backend/functions/get_detail/` | イベント詳細を取得 |
| get_event | `src/backend/functions/get_event/` | イベント情報を取得 |
| update_event | `src/backend/functions/update_event/` | イベント情報を更新 |
| init_db | `src/backend/functions/init_db/` | データベースを初期化 |

### Lambda Layer

**Layer** - 共有Pythonモジュール：
- `logging_utils.py` - ログ出力ユーティリティ
- `secret_utils.py` - Secrets Manager連携
- `ssm_utils.py` - Systems Manager パラメータストア連携
- `user_utils.py` - ユーザー情報取得（API Gateway 経由の Cognito 認証情報からユーザーID・ユーザー名を抽出）

**Layer2** - pymysqlライブラリ（データベース接続）

## フロントエンド

### 認証画面

- **index.html** - ログイン画面
- **change-password.html** - パスワード変更
- **change-initial-password.html** - 初期パスワード変更

### メイン機能

- **get-calendar.html** - カレンダービュー
- **add-event.html** - イベント追加
- **edit-event.html** - イベント編集
- **get-detail.html** - イベント詳細表示

### スタイリング

- **css/style.css** - アプリケーション全体のスタイル

## セキュリティ考慮事項

- **VPC** - プライベートサブネット内でRDSを実行
- **KMS暗号化** - S3とRDSのデータ暗号化
- **Secrets Manager** - データベース認証情報の安全な管理
- **Cognito** - エンタープライズグレードの認証

## データベースの初期化

デプロイ完了時に `init_db` Lambda 関数が実行され、  
データベースに必要なテーブルの作成および初期データ（日付情報・祝日情報）の投入を行います。

本処理は再実行可能な設計となっており、既存データは保持されます。

## 今後の課題

プログラミング技術の向上と AWS サービスへの理解を深めるため、以下の改善に取り組む予定です。

- 各コードのリファクタリング
  - フロントエンド
    - async/await と .then が混在しているため、構文を統一（2/4済）
    - CognitoのSDK利用（現状は、APIを直接fetchしているため）
    - ユーザーインターフェースの改善（より直感的な操作を可能にする）
    - エラー処理の拡充（2/4済）
  - バックエンド
    - オブジェクト指向設計への移行 (2/7済) 
      現状は関数中心の構成のため、クラスやメソッドを用いた設計へリファクタリング
- インフラ関連
  - データベースを DynamoDB へ移行
  - CDK を TypeScript へ移植

## 不具合

- Firefoxを使用すると、ログイン後、カレンダー画面が正常に表示できない（修正済）
  - get-calendar.jsのページ表示時のイベントフローを修正

---

**最終更新**: 2026年2月7日
