
import os
import io
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, flash, session,
    g, send_file, abort
)
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ceipc-secretaria-2026")

STORAGE_DIR = os.environ.get("RENDER_DISK_PATH", "/opt/render/project/src/storage")
if not os.path.isdir(STORAGE_DIR):
    os.makedirs(STORAGE_DIR, exist_ok=True)

DB_NAME = os.path.join(STORAGE_DIR, "escola.db")
PASSING_GRADE = 7.0


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def table_columns(cursor, table_name):
    return {row[1] for row in cursor.execute(f"PRAGMA table_info({table_name})").fetchall()}


def ensure_column(cursor, table_name, column_name, column_type_sql):
    existing = table_columns(cursor, table_name)
    if column_name not in existing:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type_sql}")


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS turmas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        serie TEXT NOT NULL,
        turno TEXT NOT NULL,
        ano_letivo TEXT NOT NULL,
        ativa INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alunos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        data_nascimento TEXT,
        codigo_aluno TEXT,
        observacoes TEXT,
        nome_mae TEXT,
        nome_pai TEXT,
        telefone_responsavel TEXT,
        cpf_aluno TEXT,
        rg_aluno TEXT,
        cpf_mae TEXT,
        rg_mae TEXT,
        cpf_pai TEXT,
        rg_pai TEXT,
        email_responsavel TEXT,
        ativo INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matriculas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aluno_id INTEGER NOT NULL,
        turma_id INTEGER NOT NULL,
        ativa INTEGER DEFAULT 1,
        data_inicio TEXT DEFAULT CURRENT_TIMESTAMP,
        data_fim TEXT,
        observacoes TEXT,
        FOREIGN KEY (aluno_id) REFERENCES alunos(id),
        FOREIGN KEY (turma_id) REFERENCES turmas(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS disciplinas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        ativa INTEGER DEFAULT 1
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS turma_disciplinas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        turma_id INTEGER NOT NULL,
        disciplina_id INTEGER NOT NULL,
        UNIQUE(turma_id, disciplina_id),
        FOREIGN KEY (turma_id) REFERENCES turmas(id),
        FOREIGN KEY (disciplina_id) REFERENCES disciplinas(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aluno_id INTEGER NOT NULL,
        turma_id INTEGER NOT NULL,
        disciplina_id INTEGER NOT NULL,
        bimestre INTEGER NOT NULL,
        nota REAL NOT NULL,
        FOREIGN KEY (aluno_id) REFERENCES alunos(id),
        FOREIGN KEY (turma_id) REFERENCES turmas(id),
        FOREIGN KEY (disciplina_id) REFERENCES disciplinas(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS boletim_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aluno_id INTEGER NOT NULL,
        turma_id INTEGER NOT NULL,
        disciplina_id INTEGER NOT NULL,

        b1_n1 REAL, b1_n2 REAL, b1_n3 REAL, b1_n4 REAL, b1_faltas INTEGER,
        b2_n1 REAL, b2_n2 REAL, b2_n3 REAL, b2_n4 REAL, b2_faltas INTEGER,
        b3_n1 REAL, b3_n2 REAL, b3_n3 REAL, b3_n4 REAL, b3_faltas INTEGER,
        b4_n1 REAL, b4_n2 REAL, b4_n3 REAL, b4_n4 REAL, b4_faltas INTEGER,

        UNIQUE(aluno_id, turma_id, disciplina_id),
        FOREIGN KEY (aluno_id) REFERENCES alunos(id),
        FOREIGN KEY (turma_id) REFERENCES turmas(id),
        FOREIGN KEY (disciplina_id) REFERENCES disciplinas(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        nome TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'secretaria',
        ativo INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        action TEXT NOT NULL,
        table_name TEXT,
        record_id INTEGER,
        details TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Migrações seguras (sem apagar dados)
    for column_name, column_type in [
        ("nome_mae", "TEXT"),
        ("nome_pai", "TEXT"),
        ("telefone_responsavel", "TEXT"),
        ("cpf_aluno", "TEXT"),
        ("rg_aluno", "TEXT"),
        ("cpf_mae", "TEXT"),
        ("rg_mae", "TEXT"),
        ("cpf_pai", "TEXT"),
        ("rg_pai", "TEXT"),
        ("email_responsavel", "TEXT"),
        ("ativo", "INTEGER DEFAULT 1"),
        ("created_at", "TEXT"),
    ]:
        ensure_column(cursor, "alunos", column_name, column_type)

    for column_name, column_type in [
        ("ativa", "INTEGER DEFAULT 1"),
        ("data_inicio", "TEXT"),
        ("data_fim", "TEXT"),
        ("observacoes", "TEXT"),
    ]:
        ensure_column(cursor, "matriculas", column_name, column_type)

    for column_name, column_type in [
        ("ativa", "INTEGER DEFAULT 1"),
        ("created_at", "TEXT"),
    ]:
        ensure_column(cursor, "turmas", column_name, column_type)

    for column_name, column_type in [
        ("ativa", "INTEGER DEFAULT 1"),
    ]:
        ensure_column(cursor, "disciplinas", column_name, column_type)

    # Corrige registros antigos sem valor nas novas colunas
    cursor.execute("UPDATE alunos SET ativo = 1 WHERE ativo IS NULL")
    cursor.execute("UPDATE turmas SET ativa = 1 WHERE ativa IS NULL")
    cursor.execute("UPDATE disciplinas SET ativa = 1 WHERE ativa IS NULL")
    cursor.execute("UPDATE matriculas SET ativa = 1 WHERE ativa IS NULL")
    cursor.execute("UPDATE matriculas SET data_inicio = COALESCE(data_inicio, CURRENT_TIMESTAMP)")
    cursor.execute("UPDATE alunos SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP)")
    cursor.execute("UPDATE turmas SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP)")

    # Cria admin inicial se não existir ninguém
    existing_user = cursor.execute("SELECT id FROM users LIMIT 1").fetchone()
    if not existing_user:
        cursor.execute(
            """
            INSERT INTO users (username, nome, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            ("admin", "Administrador", generate_password_hash("admin123"), "admin")
        )

    conn.commit()
    conn.close()


def log_action(action, table_name=None, record_id=None, details=None):
    try:
        conn = get_connection()
        user_id = session.get("user_id")
        username = session.get("username")
        conn.execute(
            """
            INSERT INTO audit_logs (user_id, username, action, table_name, record_id, details)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, action, table_name, record_id, details)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def current_timestamp():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def media_notas(*values):
    nums = [float(v) for v in values if v not in (None, "", "None")]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 1)


def media_anual(medias):
    nums = [float(v) for v in medias if v not in (None, "", "None")]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 1)


def resultado_por_media(media):
    if media is None:
        return ""
    return "APROVADO" if media >= PASSING_GRADE else "RECUPERAÇÃO"


def nota_css_class(media):
    if media is None:
        return ""
    return "media-ok" if media >= PASSING_GRADE else "media-bad"


def format_nota(value):
    if value in (None, ""):
        return ""
    return f"{float(value):.1f}".replace(".", ",")


def aluno_com_turma(conn, aluno_id):
    return conn.execute(
        """
        SELECT alunos.*,
               turmas.id AS turma_id,
               turmas.nome AS turma_nome,
               turmas.serie AS turma_serie,
               turmas.turno AS turma_turno,
               turmas.ano_letivo
        FROM alunos
        LEFT JOIN matriculas
            ON matriculas.aluno_id = alunos.id
           AND matriculas.ativa = 1
        LEFT JOIN turmas ON turmas.id = matriculas.turma_id
        WHERE alunos.id = ?
        """,
        (aluno_id,),
    ).fetchone()


def turma_atual_do_aluno(conn, aluno_id):
    return conn.execute(
        """
        SELECT turma_id, id
        FROM matriculas
        WHERE aluno_id = ? AND ativa = 1
        ORDER BY id DESC LIMIT 1
        """,
        (aluno_id,)
    ).fetchone()


def atualizar_turma_aluno(conn, aluno_id, nova_turma_id, observacao="Alteração manual de turma"):
    atual = turma_atual_do_aluno(conn, aluno_id)
    if not nova_turma_id:
        if atual:
            conn.execute(
                "UPDATE matriculas SET ativa = 0, data_fim = CURRENT_TIMESTAMP, observacoes = ? WHERE id = ?",
                ("Matrícula desativada", atual["id"])
            )
        return

    nova_turma_id = int(nova_turma_id)
    if atual and int(atual["turma_id"]) == nova_turma_id:
        return

    if atual:
        conn.execute(
            "UPDATE matriculas SET ativa = 0, data_fim = CURRENT_TIMESTAMP, observacoes = ? WHERE id = ?",
            (observacao, atual["id"])
        )

    conn.execute(
        """
        INSERT INTO matriculas (aluno_id, turma_id, ativa, data_inicio, observacoes)
        VALUES (?, ?, 1, CURRENT_TIMESTAMP, ?)
        """,
        (aluno_id, nova_turma_id, observacao)
    )


@app.before_request
def load_logged_user():
    user_id = session.get("user_id")
    g.user = None
    if user_id:
        conn = get_connection()
        g.user = conn.execute(
            "SELECT * FROM users WHERE id = ? AND ativo = 1",
            (user_id,)
        ).fetchone()
        conn.close()


@app.context_processor
def inject_global_vars():
    logo_exists = os.path.exists(os.path.join(app.static_folder, "logo-escola.png"))
    return dict(
        media_notas=media_notas,
        media_anual=media_anual,
        resultado_por_media=resultado_por_media,
        nota_css_class=nota_css_class,
        format_nota=format_nota,
        PASSING_GRADE=PASSING_GRADE,
        logo_exists=logo_exists,
        current_year=datetime.now().year,
        now_label=current_timestamp(),
    )


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("login", next=request.path))
        return view(**kwargs)
    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("login", next=request.path))
        if g.user["role"] != "admin":
            flash("Acesso restrito ao administrador.")
            return redirect(url_for("index"))
        return view(**kwargs)
    return wrapped_view


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = get_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND ativo = 1",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            log_action("LOGIN", "users", user["id"], f"Usuário {username} entrou no sistema")
            flash("Login realizado com sucesso.")
            next_url = request.args.get("next") or url_for("index")
            return redirect(next_url)

        flash("Usuário ou senha inválidos.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    if session.get("username"):
        log_action("LOGOUT", "users", session.get("user_id"), f"Usuário {session.get('username')} saiu do sistema")
    session.clear()
    flash("Sessão encerrada.")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    conn = get_connection()

    total_alunos = conn.execute("SELECT COUNT(*) AS total FROM alunos WHERE ativo = 1").fetchone()["total"]
    total_turmas = conn.execute("SELECT COUNT(*) AS total FROM turmas WHERE ativa = 1").fetchone()["total"]
    total_disciplinas = conn.execute("SELECT COUNT(*) AS total FROM disciplinas WHERE ativa = 1").fetchone()["total"]
    total_boletins = conn.execute("SELECT COUNT(*) AS total FROM boletim_itens").fetchone()["total"]
    total_usuarios = conn.execute("SELECT COUNT(*) AS total FROM users WHERE ativo = 1").fetchone()["total"]

    conn.close()

    return render_template(
        "index.html",
        total_alunos=total_alunos,
        total_turmas=total_turmas,
        total_disciplinas=total_disciplinas,
        total_boletins=total_boletins,
        total_usuarios=total_usuarios,
    )


@app.route("/turmas", methods=["GET", "POST"])
@login_required
def turmas():
    conn = get_connection()

    if request.method == "POST":
        nome = request.form["nome"].strip()
        serie = request.form["serie"].strip()
        turno = request.form["turno"].strip()
        ano_letivo = request.form["ano_letivo"].strip()

        if nome and serie and turno and ano_letivo:
            cursor = conn.execute(
                "INSERT INTO turmas (nome, serie, turno, ano_letivo) VALUES (?, ?, ?, ?)",
                (nome, serie, turno, ano_letivo),
            )
            conn.commit()
            log_action("CRIAR_TURMA", "turmas", cursor.lastrowid, f"{nome} / {serie} / {ano_letivo}")
            flash("Turma cadastrada com sucesso.")
            conn.close()
            return redirect(url_for("turmas"))

    lista_turmas = conn.execute(
        "SELECT * FROM turmas WHERE ativa = 1 ORDER BY ano_letivo DESC, serie ASC, nome ASC"
    ).fetchall()
    conn.close()
    return render_template("turmas.html", turmas=lista_turmas)


@app.route("/turmas/<int:turma_id>/disciplinas", methods=["GET", "POST"])
@login_required
def turma_disciplinas(turma_id):
    conn = get_connection()
    turma = conn.execute("SELECT * FROM turmas WHERE id = ? AND ativa = 1", (turma_id,)).fetchone()
    if not turma:
        conn.close()
        flash("Turma não encontrada.")
        return redirect(url_for("turmas"))

    if request.method == "POST":
        selecionadas = request.form.getlist("disciplinas")
        conn.execute("DELETE FROM turma_disciplinas WHERE turma_id = ?", (turma_id,))
        for disciplina_id in selecionadas:
            conn.execute(
                "INSERT OR IGNORE INTO turma_disciplinas (turma_id, disciplina_id) VALUES (?, ?)",
                (turma_id, disciplina_id),
            )
        conn.commit()
        log_action("VINCULAR_DISCIPLINAS_TURMA", "turma_disciplinas", turma_id, f"Turma {turma['nome']} atualizada")
        flash("Disciplinas da turma atualizadas com sucesso.")
        conn.close()
        return redirect(url_for("turma_disciplinas", turma_id=turma_id))

    disciplinas = conn.execute(
        "SELECT * FROM disciplinas WHERE ativa = 1 ORDER BY nome ASC"
    ).fetchall()
    selecionadas = {
        row["disciplina_id"]
        for row in conn.execute(
            "SELECT disciplina_id FROM turma_disciplinas WHERE turma_id = ?", (turma_id,)
        ).fetchall()
    }
    conn.close()
    return render_template(
        "turma_disciplinas.html",
        turma=turma,
        disciplinas=disciplinas,
        selecionadas=selecionadas,
    )


@app.route("/alunos", methods=["GET", "POST"])
@login_required
def alunos():
    conn = get_connection()

    if request.method == "POST":
        payload = {
            "nome": request.form.get("nome", "").strip(),
            "data_nascimento": request.form.get("data_nascimento", "").strip(),
            "codigo_aluno": request.form.get("codigo_aluno", "").strip(),
            "observacoes": request.form.get("observacoes", "").strip(),
            "nome_mae": request.form.get("nome_mae", "").strip(),
            "nome_pai": request.form.get("nome_pai", "").strip(),
            "telefone_responsavel": request.form.get("telefone_responsavel", "").strip(),
            "email_responsavel": request.form.get("email_responsavel", "").strip(),
            "cpf_aluno": request.form.get("cpf_aluno", "").strip(),
            "rg_aluno": request.form.get("rg_aluno", "").strip(),
            "cpf_mae": request.form.get("cpf_mae", "").strip(),
            "rg_mae": request.form.get("rg_mae", "").strip(),
            "cpf_pai": request.form.get("cpf_pai", "").strip(),
            "rg_pai": request.form.get("rg_pai", "").strip(),
        }
        turma_id = request.form.get("turma_id", "").strip()

        if payload["nome"]:
            cursor = conn.execute(
                """
                INSERT INTO alunos
                (nome, data_nascimento, codigo_aluno, observacoes,
                 nome_mae, nome_pai, telefone_responsavel, email_responsavel,
                 cpf_aluno, rg_aluno, cpf_mae, rg_mae, cpf_pai, rg_pai)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["nome"], payload["data_nascimento"], payload["codigo_aluno"], payload["observacoes"],
                    payload["nome_mae"], payload["nome_pai"], payload["telefone_responsavel"], payload["email_responsavel"],
                    payload["cpf_aluno"], payload["rg_aluno"], payload["cpf_mae"], payload["rg_mae"],
                    payload["cpf_pai"], payload["rg_pai"],
                ),
            )
            aluno_id = cursor.lastrowid
            if turma_id:
                atualizar_turma_aluno(conn, aluno_id, turma_id, "Vínculo inicial do aluno")
            conn.commit()
            log_action("CRIAR_ALUNO", "alunos", aluno_id, payload["nome"])
            flash("Aluno cadastrado com sucesso.")
            conn.close()
            return redirect(url_for("alunos"))

        flash("Nome do aluno é obrigatório.")

    lista_turmas = conn.execute(
        "SELECT * FROM turmas WHERE ativa = 1 ORDER BY ano_letivo DESC, serie ASC, nome ASC"
    ).fetchall()

    lista_alunos = conn.execute(
        """
        SELECT alunos.*,
               turmas.nome AS turma_nome,
               turmas.serie AS turma_serie,
               turmas.ano_letivo AS turma_ano
        FROM alunos
        LEFT JOIN matriculas
            ON matriculas.aluno_id = alunos.id
           AND matriculas.ativa = 1
        LEFT JOIN turmas ON turmas.id = matriculas.turma_id
        WHERE alunos.ativo = 1
        ORDER BY alunos.nome ASC
        """
    ).fetchall()

    conn.close()
    return render_template("alunos.html", alunos=lista_alunos, turmas=lista_turmas)


@app.route("/alunos/<int:aluno_id>/editar", methods=["GET", "POST"])
@login_required
def editar_aluno(aluno_id):
    conn = get_connection()
    aluno = aluno_com_turma(conn, aluno_id)
    if not aluno or not aluno["ativo"]:
        conn.close()
        flash("Aluno não encontrado.")
        return redirect(url_for("alunos"))

    if request.method == "POST":
        payload = {
            "nome": request.form.get("nome", "").strip(),
            "data_nascimento": request.form.get("data_nascimento", "").strip(),
            "codigo_aluno": request.form.get("codigo_aluno", "").strip(),
            "observacoes": request.form.get("observacoes", "").strip(),
            "nome_mae": request.form.get("nome_mae", "").strip(),
            "nome_pai": request.form.get("nome_pai", "").strip(),
            "telefone_responsavel": request.form.get("telefone_responsavel", "").strip(),
            "email_responsavel": request.form.get("email_responsavel", "").strip(),
            "cpf_aluno": request.form.get("cpf_aluno", "").strip(),
            "rg_aluno": request.form.get("rg_aluno", "").strip(),
            "cpf_mae": request.form.get("cpf_mae", "").strip(),
            "rg_mae": request.form.get("rg_mae", "").strip(),
            "cpf_pai": request.form.get("cpf_pai", "").strip(),
            "rg_pai": request.form.get("rg_pai", "").strip(),
        }
        nova_turma_id = request.form.get("turma_id", "").strip()

        conn.execute(
            """
            UPDATE alunos
            SET nome = ?, data_nascimento = ?, codigo_aluno = ?, observacoes = ?,
                nome_mae = ?, nome_pai = ?, telefone_responsavel = ?, email_responsavel = ?,
                cpf_aluno = ?, rg_aluno = ?, cpf_mae = ?, rg_mae = ?, cpf_pai = ?, rg_pai = ?
            WHERE id = ?
            """,
            (
                payload["nome"], payload["data_nascimento"], payload["codigo_aluno"], payload["observacoes"],
                payload["nome_mae"], payload["nome_pai"], payload["telefone_responsavel"], payload["email_responsavel"],
                payload["cpf_aluno"], payload["rg_aluno"], payload["cpf_mae"], payload["rg_mae"],
                payload["cpf_pai"], payload["rg_pai"], aluno_id
            )
        )

        atualizar_turma_aluno(conn, aluno_id, nova_turma_id, "Alteração de turma no cadastro do aluno")
        conn.commit()
        log_action("EDITAR_ALUNO", "alunos", aluno_id, f"Cadastro atualizado: {payload['nome']}")
        flash("Cadastro do aluno atualizado com sucesso.")
        conn.close()
        return redirect(url_for("alunos"))

    turmas = conn.execute(
        "SELECT * FROM turmas WHERE ativa = 1 ORDER BY ano_letivo DESC, serie ASC, nome ASC"
    ).fetchall()
    historico_turmas = conn.execute(
        """
        SELECT matriculas.*, turmas.nome AS turma_nome, turmas.serie, turmas.turno, turmas.ano_letivo
        FROM matriculas
        INNER JOIN turmas ON turmas.id = matriculas.turma_id
        WHERE matriculas.aluno_id = ?
        ORDER BY matriculas.id DESC
        """,
        (aluno_id,)
    ).fetchall()
    conn.close()
    return render_template("aluno_editar.html", aluno=aluno, turmas=turmas, historico_turmas=historico_turmas)


@app.route("/alunos/<int:aluno_id>/excluir", methods=["GET", "POST"])
@login_required
def excluir_aluno(aluno_id):
    conn = get_connection()
    aluno = aluno_com_turma(conn, aluno_id)
    if not aluno or not aluno["ativo"]:
        conn.close()
        flash("Aluno não encontrado.")
        return redirect(url_for("alunos"))

    if request.method == "POST":
        confirmation_text = request.form.get("confirmation_text", "").strip().upper()
        confirmation_name = request.form.get("confirmation_name", "").strip()
        if confirmation_text != "EXCLUIR" or confirmation_name != aluno["nome"]:
            flash('Confirmação inválida. Digite EXCLUIR e o nome completo do aluno.')
        else:
            conn.execute("UPDATE alunos SET ativo = 0 WHERE id = ?", (aluno_id,))
            conn.execute(
                "UPDATE matriculas SET ativa = 0, data_fim = CURRENT_TIMESTAMP, observacoes = ? WHERE aluno_id = ? AND ativa = 1",
                ("Exclusão lógica do cadastro", aluno_id)
            )
            conn.commit()
            log_action("EXCLUIR_ALUNO", "alunos", aluno_id, f"Exclusão lógica do aluno {aluno['nome']}")
            flash("Aluno excluído com segurança.")
            conn.close()
            return redirect(url_for("alunos"))

    conn.close()
    return render_template("aluno_excluir.html", aluno=aluno)


@app.route("/disciplinas", methods=["GET", "POST"])
@login_required
def disciplinas():
    conn = get_connection()

    if request.method == "POST":
        nome = request.form["nome"].strip()
        if nome:
            try:
                cursor = conn.execute("INSERT INTO disciplinas (nome) VALUES (?)", (nome,))
                conn.commit()
                log_action("CRIAR_DISCIPLINA", "disciplinas", cursor.lastrowid, nome)
                flash("Disciplina cadastrada com sucesso.")
            except sqlite3.IntegrityError:
                flash("Essa disciplina já existe.")
            conn.close()
            return redirect(url_for("disciplinas"))

    lista_disciplinas = conn.execute(
        "SELECT * FROM disciplinas WHERE ativa = 1 ORDER BY nome ASC"
    ).fetchall()
    conn.close()
    return render_template("disciplinas.html", disciplinas=lista_disciplinas)


@app.route("/notas", methods=["GET", "POST"])
@login_required
def notas():
    conn = get_connection()

    if request.method == "POST":
        aluno_id = request.form["aluno_id"]
        turma_id = request.form["turma_id"]
        disciplina_id = request.form["disciplina_id"]
        bimestre = request.form["bimestre"]
        nota = request.form["nota"]

        conn.execute(
            """
            INSERT INTO notas (aluno_id, turma_id, disciplina_id, bimestre, nota)
            VALUES (?, ?, ?, ?, ?)
            """,
            (aluno_id, turma_id, disciplina_id, bimestre, nota),
        )
        conn.commit()
        log_action("LANCAR_NOTA_SIMPLES", "notas", None, f"Aluno {aluno_id}, disciplina {disciplina_id}, bimestre {bimestre}")
        conn.close()
        flash("Nota lançada com sucesso.")
        return redirect(url_for("notas"))

    lista_alunos = conn.execute(
        """
        SELECT alunos.id, alunos.nome, turmas.nome AS turma_nome
        FROM alunos
        LEFT JOIN matriculas
            ON matriculas.aluno_id = alunos.id
           AND matriculas.ativa = 1
        LEFT JOIN turmas ON turmas.id = matriculas.turma_id
        WHERE alunos.ativo = 1
        ORDER BY alunos.nome ASC
        """
    ).fetchall()

    lista_turmas = conn.execute("SELECT * FROM turmas WHERE ativa = 1 ORDER BY nome ASC").fetchall()
    lista_disciplinas = conn.execute("SELECT * FROM disciplinas WHERE ativa = 1 ORDER BY nome ASC").fetchall()

    conn.close()
    return render_template(
        "notas.html",
        alunos=lista_alunos,
        turmas=lista_turmas,
        disciplinas=lista_disciplinas,
    )


@app.route("/notas/listar")
@login_required
def listar_notas():
    conn = get_connection()

    turma_id = request.args.get("turma_id", "").strip()
    query = """
        SELECT
            notas.id,
            alunos.nome AS aluno_nome,
            turmas.nome AS turma_nome,
            disciplinas.nome AS disciplina_nome,
            notas.bimestre,
            notas.nota
        FROM notas
        INNER JOIN alunos ON alunos.id = notas.aluno_id
        INNER JOIN turmas ON turmas.id = notas.turma_id
        INNER JOIN disciplinas ON disciplinas.id = notas.disciplina_id
    """
    params = []
    if turma_id:
        query += " WHERE turmas.id = ? "
        params.append(turma_id)
    query += " ORDER BY turmas.nome ASC, alunos.nome ASC, disciplinas.nome ASC, notas.bimestre ASC "
    lista_notas = conn.execute(query, params).fetchall()
    lista_turmas = conn.execute("SELECT * FROM turmas WHERE ativa = 1 ORDER BY nome ASC").fetchall()
    conn.close()
    return render_template("listar_notas.html", notas=lista_notas, turmas=lista_turmas, turma_id=turma_id)


@app.route("/diario", methods=["GET", "POST"])
@login_required
def diario():
    conn = get_connection()
    turma_id = request.values.get("turma_id", "").strip()
    aluno_id = request.values.get("aluno_id", "").strip()

    if request.method == "POST" and turma_id and aluno_id:
        disciplinas_da_turma = conn.execute(
            """
            SELECT disciplinas.*
            FROM turma_disciplinas
            INNER JOIN disciplinas ON disciplinas.id = turma_disciplinas.disciplina_id
            WHERE turma_disciplinas.turma_id = ?
            ORDER BY disciplinas.nome ASC
            """,
            (turma_id,),
        ).fetchall()

        campos = [
            "b1_n1", "b1_n2", "b1_n3", "b1_n4", "b1_faltas",
            "b2_n1", "b2_n2", "b2_n3", "b2_n4", "b2_faltas",
            "b3_n1", "b3_n2", "b3_n3", "b3_n4", "b3_faltas",
            "b4_n1", "b4_n2", "b4_n3", "b4_n4", "b4_faltas",
        ]

        for disciplina in disciplinas_da_turma:
            disciplina_id = disciplina["id"]
            existe = conn.execute(
                "SELECT id FROM boletim_itens WHERE aluno_id = ? AND turma_id = ? AND disciplina_id = ?",
                (aluno_id, turma_id, disciplina_id),
            ).fetchone()

            valores = {}
            for campo in campos:
                bruto = request.form.get(f"{disciplina_id}_{campo}", "").strip()
                if bruto == "":
                    valores[campo] = None
                else:
                    valores[campo] = int(bruto) if "faltas" in campo else float(bruto)

            if existe:
                set_clause = ", ".join([f"{campo} = ?" for campo in campos])
                parametros = [valores[campo] for campo in campos] + [existe["id"]]
                conn.execute(f"UPDATE boletim_itens SET {set_clause} WHERE id = ?", parametros)
            else:
                colunas = ", ".join(["aluno_id", "turma_id", "disciplina_id"] + campos)
                placeholders = ", ".join(["?" for _ in range(3 + len(campos))])
                parametros = [aluno_id, turma_id, disciplina_id] + [valores[campo] for campo in campos]
                conn.execute(
                    f"INSERT INTO boletim_itens ({colunas}) VALUES ({placeholders})",
                    parametros,
                )

        conn.commit()
        log_action("SALVAR_DIARIO", "boletim_itens", int(aluno_id), f"Diário salvo do aluno {aluno_id}")
        flash("Diário do aluno salvo com sucesso.")
        conn.close()
        return redirect(url_for("diario", turma_id=turma_id, aluno_id=aluno_id))

    turmas = conn.execute(
        "SELECT * FROM turmas WHERE ativa = 1 ORDER BY ano_letivo DESC, serie ASC, nome ASC"
    ).fetchall()
    alunos = []
    aluno = None
    disciplinas_linhas = []

    if turma_id:
        alunos = conn.execute(
            """
            SELECT alunos.*
            FROM matriculas
            INNER JOIN alunos ON alunos.id = matriculas.aluno_id
            WHERE matriculas.turma_id = ?
              AND matriculas.ativa = 1
              AND alunos.ativo = 1
            ORDER BY alunos.nome ASC
            """,
            (turma_id,),
        ).fetchall()

    if turma_id and aluno_id:
        aluno = aluno_com_turma(conn, aluno_id)
        disciplinas_da_turma = conn.execute(
            """
            SELECT disciplinas.*
            FROM turma_disciplinas
            INNER JOIN disciplinas ON disciplinas.id = turma_disciplinas.disciplina_id
            WHERE turma_disciplinas.turma_id = ?
            ORDER BY disciplinas.nome ASC
            """,
            (turma_id,),
        ).fetchall()

        for disciplina in disciplinas_da_turma:
            item = conn.execute(
                "SELECT * FROM boletim_itens WHERE aluno_id = ? AND turma_id = ? AND disciplina_id = ?",
                (aluno_id, turma_id, disciplina["id"]),
            ).fetchone()
            disciplinas_linhas.append({"disciplina": disciplina, "item": item})

    conn.close()
    return render_template(
        "diario.html",
        turmas=turmas,
        alunos=alunos,
        turma_id=turma_id,
        aluno_id=aluno_id,
        aluno=aluno,
        disciplinas_linhas=disciplinas_linhas,
    )


@app.route("/boletim/<int:aluno_id>")
@login_required
def boletim(aluno_id):
    conn = get_connection()
    aluno = aluno_com_turma(conn, aluno_id)
    if not aluno:
        conn.close()
        flash("Aluno não encontrado.")
        return redirect(url_for("alunos"))

    linhas = conn.execute(
        """
        SELECT boletim_itens.*, disciplinas.nome AS disciplina_nome
        FROM boletim_itens
        INNER JOIN disciplinas ON disciplinas.id = boletim_itens.disciplina_id
        WHERE boletim_itens.aluno_id = ? AND boletim_itens.turma_id = ?
        ORDER BY disciplinas.nome ASC
        """,
        (aluno_id, aluno["turma_id"]),
    ).fetchall()

    historico_matriculas = conn.execute(
        """
        SELECT matriculas.*, turmas.nome AS turma_nome, turmas.serie, turmas.turno, turmas.ano_letivo
        FROM matriculas
        INNER JOIN turmas ON turmas.id = matriculas.turma_id
        WHERE matriculas.aluno_id = ?
        ORDER BY turmas.ano_letivo DESC, matriculas.id DESC
        """,
        (aluno_id,)
    ).fetchall()
    conn.close()
    return render_template("boletim.html", aluno=aluno, linhas=linhas, historico_matriculas=historico_matriculas)


@app.route("/historico-transferencia/<int:aluno_id>")
@login_required
def historico_transferencia(aluno_id):
    conn = get_connection()
    aluno = aluno_com_turma(conn, aluno_id)
    if not aluno:
        conn.close()
        flash("Aluno não encontrado.")
        return redirect(url_for("alunos"))

    linhas = conn.execute(
        """
        SELECT boletim_itens.*, disciplinas.nome AS disciplina_nome
        FROM boletim_itens
        INNER JOIN disciplinas ON disciplinas.id = boletim_itens.disciplina_id
        WHERE boletim_itens.aluno_id = ? AND boletim_itens.turma_id = ?
        ORDER BY disciplinas.nome ASC
        """,
        (aluno_id, aluno["turma_id"]),
    ).fetchall()

    historico_matriculas = conn.execute(
        """
        SELECT matriculas.*, turmas.nome AS turma_nome, turmas.serie, turmas.turno, turmas.ano_letivo
        FROM matriculas
        INNER JOIN turmas ON turmas.id = matriculas.turma_id
        WHERE matriculas.aluno_id = ?
        ORDER BY turmas.ano_letivo DESC, matriculas.id DESC
        """,
        (aluno_id,)
    ).fetchall()
    conn.close()
    return render_template("historico_transferencia.html", aluno=aluno, linhas=linhas, historico_matriculas=historico_matriculas)


@app.route("/buscar")
@login_required
def buscar():
    conn = get_connection()
    termo = request.args.get("q", "").strip()
    resultados = []
    if termo:
        like = f"%{termo}%"
        resultados = conn.execute(
            """
            SELECT alunos.id, alunos.nome, alunos.codigo_aluno, alunos.nome_mae, alunos.nome_pai,
                   alunos.telefone_responsavel, alunos.cpf_aluno, alunos.rg_aluno,
                   alunos.cpf_mae, alunos.rg_mae, alunos.cpf_pai, alunos.rg_pai,
                   turmas.nome AS turma_nome, turmas.serie AS turma_serie, turmas.ano_letivo
            FROM alunos
            LEFT JOIN matriculas ON matriculas.aluno_id = alunos.id AND matriculas.ativa = 1
            LEFT JOIN turmas ON turmas.id = matriculas.turma_id
            WHERE alunos.ativo = 1 AND (
                   alunos.nome LIKE ?
                OR alunos.codigo_aluno LIKE ?
                OR alunos.nome_mae LIKE ?
                OR alunos.nome_pai LIKE ?
                OR alunos.telefone_responsavel LIKE ?
                OR alunos.cpf_aluno LIKE ?
                OR alunos.rg_aluno LIKE ?
                OR alunos.cpf_mae LIKE ?
                OR alunos.rg_mae LIKE ?
                OR alunos.cpf_pai LIKE ?
                OR alunos.rg_pai LIKE ?
                OR turmas.nome LIKE ?
                OR turmas.serie LIKE ?
            )
            ORDER BY alunos.nome ASC
            """,
            (like, like, like, like, like, like, like, like, like, like, like, like, like),
        ).fetchall()
    conn.close()
    return render_template("buscar.html", termo=termo, resultados=resultados)


@app.route("/admin/usuarios", methods=["GET", "POST"])
@admin_required
def admin_usuarios():
    conn = get_connection()
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "secretaria").strip()

        if nome and username and password:
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO users (nome, username, password_hash, role)
                    VALUES (?, ?, ?, ?)
                    """,
                    (nome, username, generate_password_hash(password), role)
                )
                conn.commit()
                log_action("CRIAR_USUARIO", "users", cursor.lastrowid, f"Usuário {username} criado")
                flash("Usuário criado com sucesso.")
                conn.close()
                return redirect(url_for("admin_usuarios"))
            except sqlite3.IntegrityError:
                flash("Esse login já existe.")
        else:
            flash("Preencha nome, login e senha.")

    usuarios = conn.execute(
        "SELECT id, nome, username, role, ativo, created_at FROM users ORDER BY nome ASC"
    ).fetchall()
    logs = conn.execute(
        "SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100"
    ).fetchall()
    conn.close()
    return render_template("admin_usuarios.html", usuarios=usuarios, logs=logs)


@app.route("/backup/exportar")
@admin_required
def backup_exportar():
    if not os.path.exists(DB_NAME):
        flash("Banco de dados não encontrado para exportação.")
        return redirect(url_for("index"))
    log_action("EXPORTAR_BACKUP", "backup", None, "Backup manual exportado")
    return send_file(
        DB_NAME,
        as_attachment=True,
        download_name=f"ceipc-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
    )


@app.route("/ajuda-migracao")
@login_required
def ajuda_migracao():
    return render_template("ajuda_migracao.html")


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
