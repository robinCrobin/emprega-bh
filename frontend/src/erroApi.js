/** Erro de consulta à API (ou ao mock), com mensagem já em português para exibir ao usuário. */
export class ErroApi extends Error {
  constructor(status, mensagem) {
    super(mensagem);
    this.name = 'ErroApi';
    this.status = status;
  }
}
