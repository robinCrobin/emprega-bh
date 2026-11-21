import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline.ckan_vagas import (
    aggregate,
    apply_occupation_mapping,
    clean_and_deduplicate,
    load_equivalence_dictionary,
    normalize_csv_text,
    normalize_text,
    occupation_key,
)


class DataPipelineTests(unittest.TestCase):
    def test_normalize_removes_accent_and_trailing_marker(self):
        self.assertEqual(normalize_text('  Técnico de informática* '), 'TECNICO DE INFORMATICA')

    def test_csv_normalization_uses_source_columns(self):
        text = 'DATA;CNPJ;IDENTIFICAÇÃO;OCUPAÇÃO;NÚMERO DE VAGAS\n01/07/2026;00;123;Servente*;5\n'
        rows = normalize_csv_text(text)
        self.assertEqual(rows[0]['DATA'], '01/07/2026')
        self.assertEqual(rows[0]['OCUPACAO'], 'Servente*')

    def test_deduplicates_same_public_vacancy_row(self):
        rows = normalize_csv_text(
            'DATA;CNPJ;IDENTIFICAÇÃO;OCUPAÇÃO;LOCAL DE TRABALHO;NÚMERO DE VAGAS;ESCOLARIDADE;EXPERIÊNCIA\n'
            '01/07/2026;00;123;Carpinteiro*;Centro/BH;5;Ensino Médio completo;6 meses\n'
            '01/07/2026;00;123;Carpinteiro*;Centro/BH;5;Ensino Médio completo;6 meses\n'
        )
        cleaned = clean_and_deduplicate(rows)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0]['nome_ocupacao_original'], 'Carpinteiro*')

    def test_aggregation_is_by_occupation_and_quarter(self):
        cleaned = [
            {'nome_padronizado': 'Auxiliar administrativo', 'codigo_cbo': '411010', 'status_validacao': 'validado', 'nome_chave_normalizada': 'aux administrativo', 'quarter': '2026-T3', 'vacancies': 5},
            {'nome_padronizado': 'Auxiliar administrativo', 'codigo_cbo': '411010', 'status_validacao': 'validado', 'nome_chave_normalizada': 'auxiliar administrativo', 'quarter': '2026-T3', 'vacancies': 3},
            {'nome_padronizado': 'Servente', 'codigo_cbo': '', 'status_validacao': 'nao_mapeado', 'nome_chave_normalizada': 'servente', 'quarter': '2026-T3', 'vacancies': 2},
        ]
        aggregated = aggregate(cleaned)
        self.assertEqual(aggregated, [
            {'nome_padronizado': 'Auxiliar administrativo', 'codigo_cbo': '411010', 'status_validacao': 'validado', 'quarter': '2026-T3', 'vacancies': 8},
            {'nome_padronizado': 'Servente', 'codigo_cbo': '', 'status_validacao': 'nao_mapeado', 'quarter': '2026-T3', 'vacancies': 2},
        ])

    def test_invalid_year_outside_catalog_range_is_rejected(self):
        rows = normalize_csv_text(
            'DATA;CNPJ;IDENTIFICAÇÃO;OCUPAÇÃO;NÚMERO DE VAGAS\n'
            '01/07/2030;00;123;Servente*;5\n'
        )
        self.assertEqual(clean_and_deduplicate(rows), [])

    def test_normalized_key_removes_punctuation_accents_and_case(self):
        self.assertEqual(occupation_key('AUX. Administrativo'), 'aux administrativo')

    def test_unmapped_occupation_is_preserved_without_cbo(self):
        mapped = apply_occupation_mapping('Auxiliar ADM.', {})
        self.assertEqual(mapped['nome_ocupacao_original'], 'Auxiliar ADM.')
        self.assertEqual(mapped['nome_padronizado'], 'Auxiliar ADM.')
        self.assertEqual(mapped['codigo_cbo'], '')
        self.assertEqual(mapped['status_validacao'], 'nao_mapeado')

    def test_dictionary_rejects_duplicate_normalized_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'mappings.csv'
            with path.open('w', newline='', encoding='utf-8') as output:
                writer = csv.DictWriter(output, fieldnames=[
                    'nome_original_referencia', 'nome_chave_normalizada', 'nome_padronizado',
                    'codigo_cbo', 'status_validacao', 'criterio_correspondencia'
                ])
                writer.writeheader()
                for name in ('AUX. ADMINISTRATIVO', 'Auxiliar Administrativo'):
                    writer.writerow({
                        'nome_original_referencia': name,
                        'nome_chave_normalizada': 'auxiliar administrativo',
                        'nome_padronizado': 'Auxiliar administrativo',
                        'codigo_cbo': '411010',
                        'status_validacao': 'validado',
                        'criterio_correspondencia': 'validacao_manual',
                    })
            with self.assertRaises(ValueError):
                load_equivalence_dictionary(path)

    def test_validated_mapping_stores_cbo_as_text(self):
        mappings = {'auxiliar administrativo': {
            'nome_original_referencia': 'Auxiliar Administrativo',
            'nome_chave_normalizada': 'auxiliar administrativo',
            'nome_padronizado': 'Auxiliar administrativo',
            'codigo_cbo': '0411010',
            'status_validacao': 'validado',
            'criterio_correspondencia': 'titulo_oficial',
        }}
        mapped = apply_occupation_mapping('Auxiliar Administrativo', mappings)
        self.assertEqual(mapped['codigo_cbo'], '0411010')

    def test_processed_shape_contains_no_personal_fields(self):
        cleaned = clean_and_deduplicate(normalize_csv_text(
            'DATA;CNPJ;IDENTIFICAÇÃO;OCUPAÇÃO;NÚMERO DE VAGAS\n01/07/2026;secret;secret;Servente*;5\n'
        ))
        aggregated = aggregate(cleaned)
        self.assertEqual(set(aggregated[0]), {'nome_padronizado', 'codigo_cbo', 'status_validacao', 'quarter', 'vacancies'})


if __name__ == '__main__':
    unittest.main()
