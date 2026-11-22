"""Testes da API (A09): busca, série, 404/422, histórico mínimo e formato das respostas."""
from conftest import inserir_ocupacao

CHAVES_SERIE = {'ocupacao', 'total_trimestres', 'serie', 'tendencia', 'historico_suficiente',
                'minimo_trimestres', 'previsao', 'motivo_sem_previsao', 'aviso', 'informacoes_usadas'}


def test_busca_ignora_acento_e_caixa(cliente, banco):
    inserir_ocupacao(banco, 'Técnico em Enfermagem', '999401', [1])
    inserir_ocupacao(banco, 'Cozinheiro', '999402', [1])
    for q in ('tecnico', 'TÉCNICO', 'enfermagem', 'enferm', 'Enfermagem tecnico'):
        r = cliente.get('/ocupacoes', params={'q': q})
        assert r.status_code == 200
        assert [o['nome'] for o in r.json()['resultados']] == ['Técnico em Enfermagem'], q
    assert set(r.json()['resultados'][0]) == {'id', 'nome', 'codigo_cbo'}


def test_busca_com_acento_na_consulta_acha_nome_sem_acento(cliente, banco):
    inserir_ocupacao(banco, 'Operador de producao', '999403', [1])
    assert cliente.get('/ocupacoes', params={'q': 'produção'}).json()['total_retornado'] == 1


def test_busca_sem_resultado_e_limite(cliente, banco):
    for i in range(5):
        inserir_ocupacao(banco, f'Auxiliar {i}', f'99950{i}', [1])
    assert cliente.get('/ocupacoes', params={'q': 'zzzz'}).json()['resultados'] == []
    assert len(cliente.get('/ocupacoes', params={'q': 'auxiliar', 'limit': 3}).json()['resultados']) == 3


def test_busca_com_caracteres_especiais_nao_quebra(cliente, banco):
    inserir_ocupacao(banco, 'Auxiliar', '999510', [1])
    for q in ("%%", "'; DROP TABLE ocupacao;--", '__'):
        assert cliente.get('/ocupacoes', params={'q': q}).status_code == 200
    assert banco.execute('SELECT count(*) FROM ocupacao').fetchone()[0] == 1


def test_busca_valida_parametros_em_portugues(cliente):
    for params in ({}, {'q': ''}, {'q': 'a'}, {'q': 'ab', 'limit': 0}):
        r = cliente.get('/ocupacoes', params=params)
        assert r.status_code == 422 and r.json()['detail'].startswith('Parâmetros inválidos')


def test_detalhe_da_ocupacao(cliente, banco):
    oid = inserir_ocupacao(banco, 'Pedreiro', '999601', [1, 2, 3])
    r = cliente.get(f'/ocupacoes/{oid}')
    assert r.status_code == 200
    assert r.json() == {'id': oid, 'nome': 'Pedreiro', 'codigo_cbo': '999601', 'total_trimestres': 3,
                        'primeiro_periodo': '2021-T1', 'ultimo_periodo': '2021-T3'}


def test_404_para_ocupacao_inexistente(cliente):
    for rota in ('/ocupacoes/999999', '/ocupacoes/999999/serie'):
        r = cliente.get(rota)
        assert r.status_code == 404 and r.json() == {'detail': 'Ocupação não encontrada.'}


def test_422_para_id_invalido(cliente):
    assert cliente.get('/ocupacoes/abc').status_code == 422
    assert cliente.get('/ocupacoes/0/serie').status_code == 422


def test_serie_ordenada_cronologicamente_e_formato(cliente, banco):
    oid = inserir_ocupacao(banco, 'Analista', '999701', [10] * 4 + [12] * 4)
    r = cliente.get(f'/ocupacoes/{oid}/serie')
    corpo = r.json()
    assert r.status_code == 200 and set(corpo) == CHAVES_SERIE
    periodos = [p['periodo'] for p in corpo['serie']]
    assert periodos == sorted(periodos) and periodos[0] == '2021-T1' and periodos[-1] == '2022-T4'
    assert set(corpo['serie'][0]) == {'periodo', 'ano', 'trimestre', 'quantidade_vagas'}
    assert corpo['tendencia']['classificacao'] == 'crescente'
    assert corpo['historico_suficiente'] is True and corpo['minimo_trimestres'] == 8


def test_historico_insuficiente_sem_previsao_e_com_motivo(cliente, banco):
    oid = inserir_ocupacao(banco, 'Cozinheiro', '999702', [5] * 7)
    corpo = cliente.get(f'/ocupacoes/{oid}/serie').json()
    assert corpo['historico_suficiente'] is False and corpo['previsao'] is None
    assert '7 trimestre' in corpo['motivo_sem_previsao'] and len(corpo['serie']) == 7
    assert corpo['tendencia']['disponivel'] is False and corpo['informacoes_usadas'] == []
    assert corpo['aviso']


def test_exatamente_oito_trimestres_e_suficiente(cliente, banco):
    oid = inserir_ocupacao(banco, 'Vendedor', '999703', [5] * 8)
    corpo = cliente.get(f'/ocupacoes/{oid}/serie').json()
    assert corpo['historico_suficiente'] is True and corpo['tendencia']['classificacao'] == 'estável'
    assert 'ainda não foi gerada' in corpo['motivo_sem_previsao']


def test_minimo_configuravel(cliente, banco, monkeypatch):
    oid = inserir_ocupacao(banco, 'Vendedor', '999704', [5] * 6)
    monkeypatch.setenv('MIN_TRIMESTRES_PREVISAO', '6')
    corpo = cliente.get(f'/ocupacoes/{oid}/serie').json()
    assert corpo['minimo_trimestres'] == 6 and corpo['historico_suficiente'] is True


def test_previsao_gravada_e_devolvida_com_contrato(cliente, banco):
    oid = inserir_ocupacao(banco, 'Analista', '999705', [10] * 8)  # último: 2022-T4
    banco.execute("INSERT INTO previsao (ocupacao_id, ano_alvo, trimestre_alvo, quantidade_prevista, algoritmo) "
                  "VALUES (%s, 2023, 1, 11.5, 'regressao_linear')", (oid,))
    corpo = cliente.get(f'/ocupacoes/{oid}/serie').json()
    assert corpo['previsao'] == {'trimestre_alvo': '2023-T1', 'quantidade_estimada': 11.5,
                                 'algoritmo': 'regressao_linear'}
    assert corpo['motivo_sem_previsao'] is None
    assert [i['chave'] for i in corpo['informacoes_usadas']] == ['historico', 'sazonalidade', 'tendencia_recente']


def test_previsao_ignorada_sem_historico_minimo(cliente, banco):
    oid = inserir_ocupacao(banco, 'Analista', '999706', [10] * 5)
    banco.execute("INSERT INTO previsao VALUES (%s, 2022, 2, 9, 'x', now())", (oid,))
    assert cliente.get(f'/ocupacoes/{oid}/serie').json()['previsao'] is None


def test_respostas_nao_expõem_dados_sensiveis(cliente, banco):
    oid = inserir_ocupacao(banco, 'Analista', '999707', [10] * 8)
    texto = (cliente.get(f'/ocupacoes/{oid}/serie').text + cliente.get('/ocupacoes?q=analista').text).lower()
    for proibido in ('cnpj', 'identificacao', 'id_vaga'):
        assert proibido not in texto


def test_openapi_documenta_rotas(cliente):
    caminhos = cliente.get('/openapi.json').json()['paths']
    assert {'/ocupacoes', '/ocupacoes/{ocupacao_id}', '/ocupacoes/{ocupacao_id}/serie'} <= set(caminhos)
