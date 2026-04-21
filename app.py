import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "ceipc-secretaria-2026"

import os

DB_NAME = os.path.join(
    os.environ.get("RENDER_DISK_PATH", "/opt/render/project/src/storage"),
    "escola.db"
)


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
        observacoes TEXT,
        nome_mae TEXT,
        nome_pai TEXT,
        telefone_responsavel TEXT,
        cpf_aluno TEXT,
        rg_aluno TEXT
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

        b1_n1 REAL,
        b1_n2 REAL,
        b1_n3 REAL,
        b1_n4 REAL,
        b1_faltas INTEGER,

        b2_n1 REAL,
        b2_n2 REAL,
        b2_n3 REAL,
        b2_n4 REAL,
        b2_faltas INTEGER,

        b3_n1 REAL,
        b3_n2 REAL,
        b3_n3 REAL,
        b3_n4 REAL,
        b3_faltas INTEGER,

        b4_n1 REAL,
        b4_n2 REAL,
        b4_n3 REAL,
        b4_n4 REAL,
        b4_faltas INTEGER,

        UNIQUE(aluno_id, turma_id, disciplina_id),
        FOREIGN KEY (aluno_id) REFERENCES alunos(id),
        FOREIGN KEY (turma_id) REFERENCES turmas(id),
        FOREIGN KEY (disciplina_id) REFERENCES disciplinas(id)
    )
    """)

    # Migração simples para bancos já existentes
    existing_columns = {row[1] for row in cursor.execute("PRAGMA table_info(alunos)").fetchall()}
    for column_name, column_type in [
        ("nome_mae", "TEXT"),
        ("nome_pai", "TEXT"),
        ("telefone_responsavel", "TEXT"),
        ("cpf_aluno", "TEXT"),
        ("rg_aluno", "TEXT"),
    ]:
        if column_name not in existing_columns:
            cursor.execute(f"ALTER TABLE alunos ADD COLUMN {column_name} {column_type}")

    conn.commit()
    conn.close()


def media_notas(*values):
    nums = [float(v) for v in values if v not in (None, "")]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 1)


def media_anual(medias):
    nums = [float(v) for v in medias if v is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 1)


def aluno_com_turma(conn, aluno_id):
    return conn.execute(
        """
        SELECT alunos.*, turmas.id AS turma_id, turmas.nome AS turma_nome, turmas.serie AS turma_serie,
               turmas.turno AS turma_turno, turmas.ano_letivo
        FROM alunos
        LEFT JOIN matriculas ON matriculas.aluno_id = alunos.id
        LEFT JOIN turmas ON turmas.id = matriculas.turma_id
        WHERE alunos.id = ?
        """,
        (aluno_id,),
    ).fetchone()


@app.context_processor
def utility_processor():
    return dict(media_notas=media_notas, media_anual=media_anual)


@app.route("/")
def index():
    conn = get_connection()

    total_alunos = conn.execute("SELECT COUNT(*) AS total FROM alunos").fetchone()["total"]
    total_turmas = conn.execute("SELECT COUNT(*) AS total FROM turmas").fetchone()["total"]
    total_disciplinas = conn.execute("SELECT COUNT(*) AS total FROM disciplinas").fetchone()["total"]
    total_notas = conn.execute("SELECT COUNT(*) AS total FROM notas").fetchone()["total"]
    total_boletins = conn.execute("SELECT COUNT(*) AS total FROM boletim_itens").fetchone()["total"]

    conn.close()

    return render_template(
        "index.html",
        total_alunos=total_alunos,
        total_turmas=total_turmas,
        total_disciplinas=total_disciplinas,
        total_notas=total_notas,
        total_boletins=total_boletins,
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
                (nome, serie, turno, ano_letivo),
            )
            conn.commit()
            flash("Turma cadastrada com sucesso.")
            conn.close()
            return redirect(url_for("turmas"))

    lista_turmas = conn.execute("SELECT * FROM turmas ORDER BY ano_letivo DESC, nome ASC").fetchall()
    conn.close()
    return render_template("turmas.html", turmas=lista_turmas)


@app.route("/turmas/<int:turma_id>/disciplinas", methods=["GET", "POST"])
def turma_disciplinas(turma_id):
    conn = get_connection()
    turma = conn.execute("SELECT * FROM turmas WHERE id = ?", (turma_id,)).fetchone()
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
        flash("Disciplinas da turma atualizadas com sucesso.")
        conn.close()
        return redirect(url_for("turma_disciplinas", turma_id=turma_id))

    disciplinas = conn.execute("SELECT * FROM disciplinas ORDER BY nome ASC").fetchall()
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
def alunos():
    conn = get_connection()

    if request.method == "POST":
        nome = request.form["nome"].strip()
        data_nascimento = request.form.get("data_nascimento", "").strip()
        codigo_aluno = request.form.get("codigo_aluno", "").strip()
        observacoes = request.form.get("observacoes", "").strip()
        nome_mae = request.form.get("nome_mae", "").strip()
        nome_pai = request.form.get("nome_pai", "").strip()
        telefone_responsavel = request.form.get("telefone_responsavel", "").strip()
        cpf_aluno = request.form.get("cpf_aluno", "").strip()
        rg_aluno = request.form.get("rg_aluno", "").strip()
        turma_id = request.form.get("turma_id")

        if nome:
            cursor = conn.execute(
                """
                INSERT INTO alunos
                (nome, data_nascimento, codigo_aluno, observacoes, nome_mae, nome_pai, telefone_responsavel, cpf_aluno, rg_aluno)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    nome,
                    data_nascimento,
                    codigo_aluno,
                    observacoes,
                    nome_mae,
                    nome_pai,
                    telefone_responsavel,
                    cpf_aluno,
                    rg_aluno,
                ),
            )
            aluno_id = cursor.lastrowid

            if turma_id:
                conn.execute(
                    "INSERT INTO matriculas (aluno_id, turma_id) VALUES (?, ?)",
                    (aluno_id, turma_id),
                )

            conn.commit()
            flash("Aluno cadastrado com sucesso.")
            conn.close()
            return redirect(url_for("alunos"))

    lista_turmas = conn.execute("SELECT * FROM turmas ORDER BY nome ASC").fetchall()

    lista_alunos = conn.execute(
        """
        SELECT alunos.*, turmas.nome AS turma_nome, turmas.serie AS turma_serie
        FROM alunos
        LEFT JOIN matriculas ON matriculas.aluno_id = alunos.id
        LEFT JOIN turmas ON turmas.id = matriculas.turma_id
        ORDER BY alunos.nome ASC
        """
    ).fetchall()

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

        conn.execute(
            """
            INSERT INTO notas (aluno_id, turma_id, disciplina_id, bimestre, nota)
            VALUES (?, ?, ?, ?, ?)
            """,
            (aluno_id, turma_id, disciplina_id, bimestre, nota),
        )
        conn.commit()
        conn.close()
        flash("Nota lançada com sucesso.")
        return redirect(url_for("notas"))

    lista_alunos = conn.execute(
        """
        SELECT alunos.id, alunos.nome, turmas.nome AS turma_nome
        FROM alunos
        LEFT JOIN matriculas ON matriculas.aluno_id = alunos.id
        LEFT JOIN turmas ON turmas.id = matriculas.turma_id
        ORDER BY alunos.nome ASC
        """
    ).fetchall()

    lista_turmas = conn.execute("SELECT * FROM turmas ORDER BY nome ASC").fetchall()
    lista_disciplinas = conn.execute("SELECT * FROM disciplinas ORDER BY nome ASC").fetchall()

    conn.close()
    return render_template(
        "notas.html",
        alunos=lista_alunos,
        turmas=lista_turmas,
        disciplinas=lista_disciplinas,
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


@app.route("/diario", methods=["GET", "POST"])
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
                    if "faltas" in campo:
                        valores[campo] = int(bruto)
                    else:
                        valores[campo] = float(bruto)

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
        flash("Diário do aluno salvo com sucesso.")
        conn.close()
        return redirect(url_for("diario", turma_id=turma_id, aluno_id=aluno_id))

    turmas = conn.execute("SELECT * FROM turmas ORDER BY nome ASC").fetchall()
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
    conn.close()
    return render_template("boletim.html", aluno=aluno, linhas=linhas)


@app.route("/buscar")
def buscar():
    conn = get_connection()
    termo = request.args.get("q", "").strip()
    resultados = []
    if termo:
        like = f"%{termo}%"
        resultados = conn.execute(
            """
            SELECT alunos.id, alunos.nome, alunos.codigo_aluno, alunos.nome_mae, alunos.nome_pai,
                   alunos.telefone_responsavel, turmas.nome AS turma_nome, turmas.serie AS turma_serie
            FROM alunos
            LEFT JOIN matriculas ON matriculas.aluno_id = alunos.id
            LEFT JOIN turmas ON turmas.id = matriculas.turma_id
            WHERE alunos.nome LIKE ?
               OR alunos.codigo_aluno LIKE ?
               OR alunos.nome_mae LIKE ?
               OR alunos.nome_pai LIKE ?
               OR alunos.telefone_responsavel LIKE ?
            ORDER BY alunos.nome ASC
            """,
            (like, like, like, like, like),
        ).fetchall()
    conn.close()
    return render_template("buscar.html", termo=termo, resultados=resultados)


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
