-- A07: esquema inicial do EmpregaBH (idempotente e reexecutável).
-- Somente dados AGREGADOS por ocupação (RNF07): nenhuma coluna de CNPJ,
-- identificador de vaga ou registro individual existe neste esquema.


-- Ocupações (identidade estável de negócio: codigo_cbo, texto com 6 dígitos).
CREATE TABLE IF NOT EXISTS ocupacao (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo_cbo        TEXT UNIQUE
                      CHECK (codigo_cbo IS NULL OR codigo_cbo ~ '^[0-9]{6}$'),
    nome              TEXT NOT NULL CHECK (length(btrim(nome)) > 0),
    -- minúsculas, sem acentos e sem pontuação; preenchido pela aplicação
    nome_normalizado  TEXT NOT NULL
);

-- pg_trgm acelera a busca por trecho do nome (LIKE '%texto%'). Se a extensao nao
-- estiver instalada no servidor, a busca continua correta, apenas sem o indice.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'pg_trgm') THEN
        CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA public;
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_ocupacao_nome_trgm '
                'ON ocupacao USING gin (nome_normalizado public.gin_trgm_ops)';
    ELSE
        RAISE NOTICE 'pg_trgm indisponivel: busca sem indice trigrama.';
    END IF;
END
$$;

-- Série histórica agregada por ocupação e trimestre.
CREATE TABLE IF NOT EXISTS vagas_trimestre (
    ocupacao_id       BIGINT   NOT NULL REFERENCES ocupacao (id) ON DELETE CASCADE,
    ano               SMALLINT NOT NULL CHECK (ano BETWEEN 1990 AND 2100),
    trimestre         SMALLINT NOT NULL CHECK (trimestre BETWEEN 1 AND 4),
    quantidade_vagas  INTEGER  NOT NULL CHECK (quantidade_vagas >= 0),
    PRIMARY KEY (ocupacao_id, ano, trimestre)
);

-- Previsões pré-calculadas (gravadas pelo modelo/A13; a API só lê).
CREATE TABLE IF NOT EXISTS previsao (
    ocupacao_id          BIGINT      NOT NULL REFERENCES ocupacao (id) ON DELETE CASCADE,
    ano_alvo             SMALLINT    NOT NULL CHECK (ano_alvo BETWEEN 1990 AND 2100),
    trimestre_alvo       SMALLINT    NOT NULL CHECK (trimestre_alvo BETWEEN 1 AND 4),
    quantidade_prevista  NUMERIC(12, 2) NOT NULL CHECK (quantidade_prevista >= 0),
    algoritmo            TEXT        NOT NULL,
    gerado_em            TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (ocupacao_id, ano_alvo, trimestre_alvo)
);

-- Métricas do modelo (MAE/RMSE); preenchida por quem treina (Davi).
CREATE TABLE IF NOT EXISTS metrica_modelo (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    algoritmo      TEXT        NOT NULL,
    mae            NUMERIC(14, 4) NOT NULL CHECK (mae >= 0),
    rmse           NUMERIC(14, 4) NOT NULL CHECK (rmse >= 0),
    data_execucao  TIMESTAMPTZ NOT NULL DEFAULT now(),
    observacoes    TEXT
);

CREATE INDEX IF NOT EXISTS idx_metrica_modelo_execucao
    ON metrica_modelo (data_execucao DESC);
