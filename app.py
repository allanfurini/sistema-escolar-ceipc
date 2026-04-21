import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "ceipc-secretaria-2026"

DB_NAME = "escola.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS turmas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        serie TEXT NOT NULL,
        turno TEXT NOT NULL,
        ano_letivo TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alunos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        data_nascimento TEXT,
        codigo_aluno TEXT,
        observacoes TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matriculas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aluno_id INTEGER NOT NULL,
        turma_id INTEGER NOT NULL,
        FOREIGN KEY (aluno_id) REFERENCES alunos(id),
        FOREIGN KEY (turma_id) REFERENCES turmas(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS disciplinas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE
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

    conn.commit()
    conn.close()


@app.route("/")
def index():
    conn = get_connection()

    total_alunos = conn.execute("SELECT COUNT(*) AS total FROM alunos").fetchone()["total"]
    total_turmas = conn.execute("SELECT COUNT(*) AS total FROM turmas").fetchone()["total"]
    total_disciplinas = conn.execute("SELECT COUNT(*) AS total FROM disciplinas").fetchone()["total"]
    total_notas = conn.execute("SELECT COUNT(*) AS total FROM notas").fetchone()["total"]

    conn.close()

    return render_template(
        "index.html",
        total_alunos=total_alunos,
        total_turmas=total_turmas,
        total_disciplinas=total_disciplinas,
        total_notas=total_notas
    )


@app.route("/turmas", methods=["GET", "POST"])
def turmas():
    conn = get_connection()

    if request.method == "POST":
        nome = request.form["nome"].strip()
        serie = request.form["serie"].strip()
        turno = request.form["turno"].strip()
        ano_letivo = request.form["ano_letivo"].strip()

        if nome and serie and turno and ano_letivo:
            conn.execute(
                "INSERT INTO turmas (nome, serie, turno, ano_letivo) VALUES (?, ?, ?, ?)",
                (nome, serie, turno, ano_letivo)
            )
            conn.commit()
            flash("Turma cadastrada com sucesso.")
            conn.close()
            return redirect(url_for("turmas"))

    lista_turmas = conn.execute("SELECT * FROM turmas ORDER BY nome ASC").fetchall()
    conn.close()
    return render_template("turmas.html", turmas=lista_turmas)


@app.route("/alunos", methods=["GET", "POST"])
def alunos():
    conn = get_connection()

    if request.method == "POST":
        nome = request.form["nome"].strip()
        data_nascimento = request.form.get("data_nascimento", "").strip()
        codigo_aluno = request.form.get("codigo_aluno", "").strip()
        observacoes = request.form.get("observacoes", "").strip()
        turma_id = request.form.get("turma_id")

        if nome:
            cursor = conn.execute(
                "INSERT INTO alunos (nome, data_nascimento, codigo_aluno, observacoes) VALUES (?, ?, ?, ?)",
                (nome, data_nascimento, codigo_aluno, observacoes)
            )
            aluno_id = cursor.lastrowid

            if turma_id:
                conn.execute(
                    "INSERT INTO matriculas (aluno_id, turma_id) VALUES (?, ?)",
                    (aluno_id, turma_id)
                )

            conn.commit()
            flash("Aluno cadastrado com sucesso.")
            conn.close()
            return redirect(url_for("alunos"))

    lista_turmas = conn.execute("SELECT * FROM turmas ORDER BY nome ASC").fetchall()

    lista_alunos = conn.execute("""
        SELECT alunos.*, turmas.nome AS turma_nome, turmas.serie AS turma_serie
        FROM alunos
        LEFT JOIN matriculas ON matriculas.aluno_id = alunos.id
        LEFT JOIN turmas ON turmas.id = matriculas.turma_id
        ORDER BY alunos.nome ASC
    """).fetchall()

    conn.close()
    return render_template("alunos.html", alunos=lista_alunos, turmas=lista_turmas)


@app.route("/disciplinas", methods=["GET", "POST"])
def disciplinas():
    conn = get_connection()

    if request.method == "POST":
        nome = request.form["nome"].strip()

        if nome:
            try:
                conn.execute("INSERT INTO disciplinas (nome) VALUES (?)", (nome,))
                conn.commit()
                flash("Disciplina cadastrada com sucesso.")
            except sqlite3.IntegrityError:
                flash("Essa disciplina já existe.")
            conn.close()
            return redirect(url_for("disciplinas"))

    lista_disciplinas = conn.execute("SELECT * FROM disciplinas ORDER BY nome ASC").fetchall()
    conn.close()
    return render_template("disciplinas.html", disciplinas=lista_disciplinas)


@app.route("/notas", methods=["GET", "POST"])
def notas():
    conn = get_connection()

    if request.method == "POST":
        aluno_id = request.form["aluno_id"]
        turma_id = request.form["turma_id"]
        disciplina_id = request.form["disciplina_id"]
        bimestre = request.form["bimestre"]
        nota = request.form["nota"]

        conn.execute("""
            INSERT INTO notas (aluno_id, turma_id, disciplina_id, bimestre, nota)
            VALUES (?, ?, ?, ?, ?)
        """, (aluno_id, turma_id, disciplina_id, bimestre, nota))
        conn.commit()
        conn.close()
        flash("Nota lançada com sucesso.")
        return redirect(url_for("notas"))

    lista_alunos = conn.execute("""
        SELECT alunos.id, alunos.nome, turmas.nome AS turma_nome
        FROM alunos
        LEFT JOIN matriculas ON matriculas.aluno_id = alunos.id
        LEFT JOIN turmas ON turmas.id = matriculas.turma_id
        ORDER BY alunos.nome ASC
    """).fetchall()

    lista_turmas = conn.execute("SELECT * FROM turmas ORDER BY nome ASC").fetchall()
    lista_disciplinas = conn.execute("SELECT * FROM disciplinas ORDER BY nome ASC").fetchall()

    conn.close()
    return render_template(
        "notas.html",
        alunos=lista_alunos,
        turmas=lista_turmas,
        disciplinas=lista_disciplinas
    )


@app.route("/notas/listar")
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
    lista_turmas = conn.execute("SELECT * FROM turmas ORDER BY nome ASC").fetchall()

    conn.close()
    return render_template("listar_notas.html", notas=lista_notas, turmas=lista_turmas, turma_id=turma_id)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
