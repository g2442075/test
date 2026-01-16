import os
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

# .env ファイルから環境変数を読み込む
load_dotenv()

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # セッション用

# PostgreSQL データベースの設定
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME')

app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql+pg8000://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLAlchemy オブジェクトの初期化
db = SQLAlchemy(app)

# ユーザーモデル
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tasks = db.relationship('Task', backref='user', lazy=True, cascade='all, delete-orphan')

# 課題モデル
class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ホーム画面：課題一覧表示（Read）
@app.route('/')
def index():
    # デモ用：ユーザーID=1で固定
    user_id = 1
    
    # 課題を締切日順で取得
    tasks = Task.query.filter_by(user_id=user_id).order_by(Task.due_date.asc()).all()
    
    # 未完了と完了済みに分ける
    incomplete_tasks = [task for task in tasks if not task.completed]
    completed_tasks = [task for task in tasks if task.completed]
    
    from datetime import date
    today = date.today()
    
    return render_template('index.html', 
                         incomplete_tasks=incomplete_tasks,
                         completed_tasks=completed_tasks,
                         today=today)

# 課題追加（Create）
@app.route('/add', methods=['POST'])
def add_task():
    try:
        user_id = 1  # デモ用固定
        title = request.form.get('title')
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date')
        
        # 入力チェック
        if not title or not due_date_str:
            flash('タイトルと締切日は必須です', 'error')
            return redirect(url_for('index'))
        
        # 日付変換
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        
        # 新しい課題を作成
        new_task = Task(
            user_id=user_id,
            title=title,
            description=description,
            due_date=due_date
        )
        
        db.session.add(new_task)
        db.session.commit()
        
        flash('課題を追加しました！', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'エラーが発生しました: {str(e)}', 'error')
        return redirect(url_for('index'))

# 完了状態の切り替え（Update）
@app.route('/toggle/<int:task_id>')
def toggle_task(task_id):
    try:
        task = Task.query.get_or_404(task_id)
        task.completed = not task.completed
        db.session.commit()
        
        status = '完了' if task.completed else '未完了'
        flash(f'課題を{status}にしました', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'エラーが発生しました: {str(e)}', 'error')
    
    return redirect(url_for('index'))

# 課題削除（Delete）
@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    try:
        task = Task.query.get_or_404(task_id)
        db.session.delete(task)
        db.session.commit()
        flash('課題を削除しました', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'エラーが発生しました: {str(e)}', 'error')
    
    return redirect(url_for('index'))

# エラーハンドリング
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.get(1):
            admin_user = User(id=1, username='admin', email='admin@example.com')
            db.session.add(admin_user)
            db.session.commit()
            print("初期ユーザーを作成しました。")
    app.run(debug=True, host='0.0.0.0', port=5000)