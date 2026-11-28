"""Testes da carga (A08) e do esquema (A07) em PostgreSQL isolado."""
import psycopg
import pytest

from app import repositorio
from app.banco.carga import ErroCarga, carregar_csv
from app.banco.cli import CSV_SEED

CABECALHO = 'nome_padronizado,codigo_cbo,status_validacao,quarter,vacancies\n'


def escrever(tmp_path, linhas):
    arquivo = tmp_path / 'entrada.csv'
    arquivo.write_text(CABECALHO + ''.join(linhas), encoding='utf-8')
    return arquivo


def contar(banco, tabela):
    return banco.execute(f'SELECT count(*) FROM {tabela}').fetchone()[0]


def test_carga_e_idempotente(banco, tmp_path):
    arq = escrever(tmp_path, ['Padeiro,999201,validado,2024-T1,5\n',
                              'Padeiro,999201,validado,2024-T2,7\n',
                              'Garçom,999202,validado,2024-T1,3\n'])
    r1 = carregar_csv(banco, arq)
    r2 = carregar_csv(banco, arq)
    assert (r1.ocupacoes, r1.linhas_vagas) == (2, 3) == (r2.ocupacoes, r2.linhas_vagas)
    assert contar(banco, 'ocupacao') == 2 and contar(banco, 'vagas_trimestre') == 3


def test_recarga_atualiza_valores_sem_duplicar(banco, tmp_path):
    carregar_csv(banco, escrever(tmp_path, ['Padeiro,999201,validado,2024-T1,5\n']))
    carregar_csv(banco, escrever(tmp_path, ['Padeiro,999201,validado,2024-T1,9\n']))
    assert banco.execute('SELECT quantidade_vagas FROM vagas_trimestre').fetchall() == [(9,)]


def test_mesmo_cbo_com_nomes_diferentes_soma_vagas_e_escolhe_nome_principal(banco, tmp_path):
    arq = escrever(tmp_path, ['Padeiro,999201,validado,2024-T1,5\n',
                              'Padeiro confeiteiro,999201,validado,2024-T1,2\n',
                              'Padeiro,999201,validado,2024-T2,4\n',
                              'Padeiro confeiteiro,999201,validado,2024-T3,1\n'])
    r = carregar_csv(banco, arq)
    assert (r.ocupacoes, r.linhas_vagas, r.linhas_consolidadas) == (1, 3, 1)
    assert banco.execute('SELECT nome FROM ocupacao').fetchall() == [('Padeiro',)]
    assert banco.execute('SELECT ano, trimestre, quantidade_vagas FROM vagas_trimestre ORDER BY 1,2').fetchall() == [
        (2024, 1, 7), (2024, 2, 4), (2024, 3, 1)]
    carregar_csv(banco, arq)  # continua idempotente
    assert contar(banco, 'vagas_trimestre') == 3


def test_linhas_nao_validadas_sao_ignoradas(banco, tmp_path):
    r = carregar_csv(banco, escrever(tmp_path, ['Padeiro,999201,validado,2024-T1,5\n',
                                                'Outro,999202,pendente,2024-T1,5\n']))
    assert r.linhas_ignoradas == 1 and contar(banco, 'ocupacao') == 1


@pytest.mark.parametrize('linha', [
    'Padeiro,999201,validado,2024-T5,5\n',      # trimestre inválido
    'Padeiro,999201,validado,2024T1,5\n',       # formato inválido
    'Padeiro,999201,validado,2024-T1,-1\n',     # negativo
    'Padeiro,999201,validado,2024-T1,abc\n',    # não inteiro
    'Padeiro,12345,validado,2024-T1,5\n',       # CBO inválido
    'Padeiro,999201,validado,2024-T1,5\nPadeiro,999201,validado,2024-T1,6\n',  # duplicada
])
def test_carga_rejeita_dados_invalidos_sem_gravar_nada(banco, tmp_path, linha):
    with pytest.raises(ErroCarga):
        carregar_csv(banco, escrever(tmp_path, [linha]))
    assert contar(banco, 'ocupacao') == 0 and contar(banco, 'vagas_trimestre') == 0


def test_carga_rejeita_colunas_ausentes(banco, tmp_path):
    arq = tmp_path / 'x.csv'
    arq.write_text('nome_padronizado,codigo_cbo\nA,123456\n', encoding='utf-8')
    with pytest.raises(ErroCarga, match='Colunas ausentes'):
        carregar_csv(banco, arq)


def test_seed_ficticio_carrega_e_tem_casos_com_e_sem_historico_minimo(banco):
    carregar_csv(banco, CSV_SEED)
    contagens = [repositorio.contar_trimestres(banco, o['id'])
                 for o in repositorio.buscar_ocupacoes(banco, 'a', 50)]
    assert any(c >= 8 for c in contagens) and any(c < 8 for c in contagens)


def test_constraints_do_esquema(banco):
    banco.execute("INSERT INTO ocupacao (codigo_cbo, nome, nome_normalizado) VALUES ('999301','X','x')")
    with pytest.raises(psycopg.errors.CheckViolation):
        banco.execute('INSERT INTO vagas_trimestre VALUES (1, 2024, 5, 1)')
    with pytest.raises(psycopg.errors.CheckViolation):
        banco.execute('INSERT INTO vagas_trimestre VALUES (1, 2024, 1, -1)')
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        banco.execute('INSERT INTO vagas_trimestre VALUES (999, 2024, 1, 1)')


def test_esquema_nao_tem_colunas_sensiveis(banco):
    colunas = {c[0].lower() for c in banco.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema = current_schema()")}
    assert not {c for c in colunas if 'cnpj' in c or 'identificacao' in c or 'id_vaga' in c}
