from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory

import fdb

# importamos a biblioteca os, que permite trabalhar com arquivos  e pastas do computador.
# Vamos utilizá-la para descobrir a extensão da imagem escolhida e definir em qual pasta ela será salva.
import os

# importa 'uuid4' para gerar nomes únicos para as imagens
# assim, dois arquivos com o mesmo nome não vão se sobrescrever
from uuid import uuid4

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='Static', template_folder='Templates', static_url_path='/static')

app.config['SECRET_KEY'] = 'chave_secreta_bolso_em_dia'

host = "localhost"
database = r"C:\Users\Aluno\Downloads\calcular_dia_trabalhado-html--main\calcular_dia_trabalhado-html--main\BANCO.FDB"
user = "sysdba"
password = "sysdba"

con = fdb.connect(host=host, database=database, user=user, password=password)

def validar_senha(senha):
    min_caractere = False
    min_upper = False
    min_lower = False
    min_num = False
    min_caractere_esp = False

    if len(senha) >= 8:
        min_caractere = True

    for caractere in senha:

        if caractere.isalpha() and caractere == caractere.upper():
            min_upper = True

        if caractere.isalpha() and caractere == caractere.lower():
            min_lower = True

        if caractere.isdigit():
            min_num = True

        if not caractere.isalpha() and not caractere.isdigit():
            min_caractere_esp = True

    if min_caractere == True and min_upper == True and min_lower == True and min_num == True and min_caractere_esp == True:
        validacao = True
        return validacao

    else:
        validacao = False
        return validacao

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pagina_cadastro')
def pagina_cadastro():
    return render_template('cadastro.html')

@app.route('/cadastrar_usuario', methods=['POST'])
def cadastrar_usuario():

    nome = request.form['nome'].strip()

    if not nome:
        flash('O nome não pode ficar vazio!', 'error')
        return redirect(url_for('pagina_cadastro'))

    email = request.form['email']
    data_nasc = request.form['data_nasc']
    telefone = request.form['telefone']
    cpf = request.form['cpf']
    senha = request.form['senha']
    confirmar = request.form['confirmar']

    cursor = con.cursor()

    try:
        cursor.execute("""SELECT 1 FROM USUARIO 
                          WHERE upper(EMAIL) = ? OR TELEFONE = ? OR CPF = ?""", (email.upper(), telefone, cpf,))

        if cursor.fetchone():
            flash('E-mail, telefone ou CPF já está sendo usado por outro usuário', 'error')
            return redirect(url_for('pagina_cadastro'))

        if confirmar != senha:
            flash('Confirmação de senha não corresponde à senha', 'error')
            return redirect(url_for('pagina_cadastro'))

        if validar_senha(senha) == True:
            senha_cripto = generate_password_hash(senha)

            session['cadastro'] = {
                'nome': nome,
                'email': email,
                'data_nasc': data_nasc,
                'telefone': telefone,
                'cpf': cpf,
                'senha': senha_cripto
            }

            return render_template('cadastro_info.html')

        else:
            flash('Senha não atende aos requisitos!', 'error')
            return redirect(url_for('pagina_cadastro'))

    except Exception as e:
        flash(f'Ocorreu um erro: {e}', 'error')
        return redirect(url_for('pagina_cadastro'))

    finally:
        cursor.close()

@app.route('/cadastrar_informacoes', methods=['POST'])
def cadastrar_informacoes():

    valor_diaria = float(request.form['valor_diaria'])
    adicional = float(request.form['adicional'])
    min_pacotes = int(request.form['min_pacotes'])

    if valor_diaria < 0 or adicional < 0 or min_pacotes < 0:
        flash('Os valores não podem ser negativos!', 'error')
        return redirect(url_for('pagina_cadastro'))

    dados = session['cadastro']
    cursor = con.cursor()
    try:
        cursor.execute("""INSERT INTO USUARIO (
                        NOME_COMPLETO, EMAIL, DATA_NASCIMENTO,
                        TELEFONE, CPF, SENHA, STATUS, TENTATIVAS,
                        VALOR_DIARIA, ADICIONAL, MIN_PACOTES
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 1, 0, ?, ?, ?)""", (dados['nome'],
                                                                    dados['email'],
                                                                    dados['data_nasc'],
                                                                    dados['telefone'],
                                                                    dados['cpf'],
                                                                    dados['senha'],
                                                                    valor_diaria,
                                                                    adicional,
                                                                    min_pacotes))
        cursor.execute("""SELECT ID_USUARIO FROM USUARIO WHERE CPF = ?""", (dados['cpf'],))

        id_usuario = cursor.fetchone()[0]

        cursor.execute("""INSERT INTO HISTORICO_SENHA (ID_USUARIO, SENHA) VALUES(?,?)""", (id_usuario, dados['senha'],))

        con.commit()

        session.pop('cadastro', None)

        return render_template('final_cadastro.html')

    except Exception as e:
        con.rollback()
        flash(f'Ocorreu um erro: {e}', 'error')
        return redirect(url_for('pagina_cadastro'))

    finally:
        cursor.close()

@app.route('/pagina_login')
def pagina_login():
    return render_template('login.html')

@app.route('/editar_movimentacao')
def editar_movimentacao():
    return render_template('editar_movimentacao.html')
@app.route('/editar_movimentacao2')
def editar_movimentacao2():
    return render_template('editar_movimentacao2.html')

@app.route('/abrir_dia-trabalhado')
def abrir_dia_trabalhado():
    return render_template('calcular_dia_trabalhado.html')
@app.route('/relatorio')
def relatorio():
    return render_template('relatorio.html')
@app.route('/categoria')
def categoria():
    return render_template('mostrar_categoria.html')

@app.route('/login', methods=['POST'])
def login():

    login = request.form['login']
    senha = request.form['senha']

    print("Login digitado:", repr(login))
    print("Tamanho:", len(login))

    cursor = con.cursor()

    try:

        if len(login) > 15:
            cursor.execute("""SELECT ID_USUARIO, SENHA, COALESCE(STATUS, 1), COALESCE(TENTATIVAS, 0) FROM USUARIO WHERE upper(EMAIL) = ?""", (login.upper(),))
        else:
            cursor.execute("""SELECT ID_USUARIO, SENHA, COALESCE(STATUS, 1), COALESCE(TENTATIVAS, 0) FROM USUARIO WHERE upper(EMAIL) = ? OR CPF = ? OR TELEFONE = ?""", (login.upper(), login, login,))

        usuario = cursor.fetchone()

        if usuario:

            if usuario[2] == 1:

                id_usuario = usuario[0]
                senha_banco = usuario[1]

                if check_password_hash(senha_banco, senha):

                    cursor.execute("""UPDATE USUARIO SET TENTATIVAS = 0 WHERE ID_USUARIO = ?""", (id_usuario, ))

                    con.commit()

                    session['id_usuario'] = id_usuario

                    return redirect(url_for('dashboard'))


                else:
                    cursor.execute("""UPDATE USUARIO SET TENTATIVAS = COALESCE(TENTATIVAS, 0) + 1 WHERE ID_USUARIO = ?""", (id_usuario,))

                    cursor.execute("""SELECT TENTATIVAS FROM USUARIO WHERE ID_USUARIO = ?""", (id_usuario,))
                    erros = cursor.fetchone()[0]

                    con.commit()

                    if erros == 3:
                        cursor.execute("""UPDATE USUARIO SET STATUS = 0 WHERE ID_USUARIO = ?""", (id_usuario,))
                        con.commit()

                        flash('USUÁRIO BLOQUEADO: 3 tentativas falhas', 'error')
                        return redirect(url_for('pagina_login'))

                    flash('Senha incorreta!', 'error')
                    return redirect(url_for('pagina_login'))

            else:
                flash('Usuário inativo!', 'error')
                return redirect(url_for('pagina_login'))

        else:
            flash('E-mail, telefone ou CPF não cadastrado!', 'error')
            return redirect(url_for('pagina_login'))

    except Exception as e:
        con.rollback()
        flash(f"Ocorreu um erro: {e}", "error")
        return redirect(url_for('pagina_login'))

    finally:
        cursor.close()

@app.route('/logout')
def logout():
    if 'id_usuario' not in session:
        return redirect(url_for('pagina_login'))

    session.pop('id_usuario', None)
    flash('Sessão encerrada. Faça login novamente.')
    return redirect(url_for('pagina_login'))

@app.route('/dashboard')
def dashboard():

    if 'id_usuario' not in session:
        flash('É necessário realizar o login', 'error')
        return redirect(url_for('pagina_login'))

    id_usuario = session['id_usuario']

    cursor = con.cursor()

    try:
        cursor.execute("""SELECT NOME_COMPLETO FROM USUARIO WHERE ID_USUARIO = ?""", (id_usuario,))

        usuario = cursor.fetchone()

        return render_template("dashboard.html", usuario=usuario[0])

    except Exception as e:
        flash(f'Ocorreu um erro: {e}', 'error')
        return redirect(url_for('pagina_login'))

    finally:
        cursor.close()

@app.route('/perfil', methods=['GET'])
def perfil():
    if 'id_usuario' not in session:
        flash('É necessário realizar o login', 'error')
        return redirect(url_for('pagina_login'))

    id_usuario = session['id_usuario']

    cursor = con.cursor()

    try:
        cursor.execute("""SELECT NOME_COMPLETO, EMAIL, DATA_NASCIMENTO, TELEFONE, CPF, VALOR_DIARIA, ADICIONAL, MIN_PACOTES, FOTO_PERFIL FROM USUARIO WHERE ID_USUARIO = ?""",(id_usuario,))

        usuario = cursor.fetchone()

        return render_template('perfil.html', usuario=usuario)

    except Exception as e:
        con.rollback()
        flash(f'Ocorreu um erro: {e}', 'error')
        return redirect(url_for('dashboard'))

    finally:
        cursor.close()



@app.route('/editar_usuario', methods=['GET','POST'])
def editar_usuario():

    if 'id_usuario' not in session:
        flash('É necessário realizar o login', 'error')
        return redirect(url_for('pagina_login'))

    id_usuario = session['id_usuario']

    cursor = con.cursor()

    try:
        cursor.execute("""SELECT NOME_COMPLETO, EMAIL, DATA_NASCIMENTO, TELEFONE, CPF, SENHA, VALOR_DIARIA, ADICIONAL, MIN_PACOTES, FOTO_PERFIL FROM USUARIO WHERE ID_USUARIO = ?""", (id_usuario,))

        usuario = cursor.fetchone()

        if request.method == 'POST':
            nome = request.form['nome'].strip()

            if not nome:
                flash('O nome não pode ficar vazio!', 'error')
                return redirect(url_for('pagina_cadastro'))

            email = request.form['email']
            data_nasc = request.form['data_nasc']
            telefone = request.form['telefone']
            cpf = request.form['cpf']
            senha_nova = request.form['senha']
            valor_diaria = float(request.form['valor_diaria'])
            adicional = float(request.form['adicional'])
            min_pacotes = int(request.form['min_pacotes'])

            if valor_diaria < 0 or adicional < 0 or min_pacotes < 0:
                flash('Os valores não podem ser negativos!', 'error')
                return redirect(url_for('pagina_cadastro'))

            cursor.execute("""SELECT 1 FROM USUARIO WHERE (upper(EMAIL) = ? OR TELEFONE = ? OR CPF = ?) AND ID_USUARIO <> ? """, (email.upper(), telefone, cpf, id_usuario))

            if cursor.fetchone():
                flash('E-mail, telefone ou CPF já está sendo usado por outro usuário', 'error')
                return redirect(url_for('editar_usuario'))

            cursor.execute("""SELECT FIRST 3 SENHA FROM HISTORICO_SENHA WHERE ID_USUARIO = ? ORDER BY DATA_ALTERACAO DESC""", (id_usuario,))
            senhas_antigas = cursor.fetchall()

            if senha_nova:

                for senha_antiga in senhas_antigas:
                    if check_password_hash(senha_antiga[0], senha_nova):

                        flash('A nova senha não pode ser igual às últimas 3 senhas!', 'error')
                        return redirect(url_for('editar_usuario'))

                if validar_senha(senha_nova):
                    senha_cripto = generate_password_hash(senha_nova)

                else:
                    flash('Senha não atende aos requisitos!', 'error')
                    return redirect(url_for('editar_usuario'))

            else:
                senha_cripto = usuario[5]


            # utilizamos request.files para pegar o arquivo enviado pelo formulário HTML.
            # o nome 'foto' precisa ser igual ao atributo name do input no HTML.
            # usamos .get() para buscar esse arquivo sem gerar um erro caso o usuário não tenha enviado nenhuma imagem.
            foto = request.files.get('foto')

            # verificamos se existe um arquivo e se ele possui um nome.
            # isso é necessário porque o usuário pode editar o perfil sem querer alterar a foto, mudando apenas o nome ou o e-mail.
            if foto and foto.filename:

                # utilizamos os.path.splitext() para separar o nome do arquivo da sua extensão.
                # O [1] pega somente a extensão.
                # por exemplo, se a imagem for chamada minha_foto.jpg, a variável extensao receberá somente '.jpg'.
                # o .lower() transforma as letras em minúsculas,evitando problemas com extensões como '.JPG' ou '.PNG'.
                extensao = os.path.splitext(foto.filename)[1].lower()

                # verificamos se a extensão da imagem é permitida.
                # caso não seja JPG, JPEG, PNG ou WEBP, mostramos uma mensagem e devolvemos o usuário para a página de edição.
                # essa é uma verificação básica pela extensão do nome do arquivo.
                if extensao not in ('.jpg', '.jpeg', '.png', '.webp'):
                    flash('Escolha uma imagem JPG, PNG ou WEBP.', 'error')
                    return redirect(url_for('editar_usuario'))

                # criamos um nome único para a imagem utilizando o ID do usuário.
                # utilizamos uuid4() para gerar um identificador aleatório, evitando que imagens diferentes sejam salvas com o mesmo nome.
                # o .hex transforma esse identificador em uma sequência de letras e números.
                # por fim, acrescentamos a extensão para manter o formato original da imagem.
                nome_foto = f'perfil_{id_usuario}_{uuid4().hex}{extensao}'

                # utilizamos foto.save() para salvar a imagem no computador.
                # app.static_folder indica a pasta Static do projeto.
                # os.path.join() junta o caminho da pasta com o nome da imagem.
                # assim, o arquivo será salvo dentro de Static/Uploads.
                foto.save(os.path.join(app.static_folder, 'Uploads', nome_foto))

                # depois de salvar a imagem na pasta, precisamos registrar o nome dela no banco de dados.
                # utilizamos UPDATE porque estamos alterando os dados de um usuário que já existe.
                # FOTO_PERFIL é a coluna que recebe o nome da imagem.
                # ID_USUARIO identifica qual usuário terá sua foto atualizada.
                cursor.execute(
                    "UPDATE USUARIO SET FOTO_PERFIL = ? WHERE ID_USUARIO = ?",
                    (nome_foto, id_usuario)
                )

            # agora, atualizamos todos os dados do usuário no banco de dados
            cursor.execute("""UPDATE USUARIO SET NOME_COMPLETO = ?, EMAIL = ?, DATA_NASCIMENTO = ?, TELEFONE = ?, CPF = ?, SENHA = ?, VALOR_DIARIA = ?, ADICIONAL = ?, MIN_PACOTES = ? WHERE ID_USUARIO = ?""",(nome, email, data_nasc, telefone, cpf, senha_cripto, valor_diaria, adicional, min_pacotes, id_usuario,))

            if senha_nova:
                cursor.execute("""INSERT INTO HISTORICO_SENHA (ID_USUARIO, SENHA) VALUES (?, ?)""",(id_usuario, senha_cripto,))

            con.commit()

            flash('Usuário editado com sucesso!', 'success')
            return redirect(url_for('perfil'))

        else:
            return render_template("editar.html", usuario=usuario)

    except Exception as e:
        con.rollback()
        print("ERRO AO EDITAR USUÁRIO:", repr(e))
        flash(f"Ocorreu um erro: {e}", "error")
        return redirect(url_for('dashboard'))

    finally:
        cursor.close()

if __name__ == "__main__":
    app.run(debug=True)