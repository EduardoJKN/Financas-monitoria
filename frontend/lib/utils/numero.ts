/** Converte texto em formato brasileiro ("1.234,56", "-85,90", "R$ 10,00")
 * para uma string decimal com ponto, pronta para enviar à API (Decimal no
 * backend). Mesma lógica de src/formatacao.py:texto_para_decimal —
 * reaproveitada em espírito, nunca passa por float/ponto flutuante aqui
 * no frontend (string -> string). */
export function paraDecimalApi(textoOriginal: string): string {
  let texto = textoOriginal.trim().replace(/R\$/gi, "").replace(/\s/g, "");
  if (!texto) throw new Error("Informe um valor.");

  let negativo = false;
  if (texto.startsWith("(") && texto.endsWith(")")) {
    negativo = true;
    texto = texto.slice(1, -1);
  }
  if (texto.startsWith("-")) {
    negativo = true;
    texto = texto.slice(1);
  } else if (texto.startsWith("+")) {
    texto = texto.slice(1);
  }

  const posVirgula = texto.lastIndexOf(",");
  const posPonto = texto.lastIndexOf(".");

  let normalizado: string;
  if (posVirgula === -1 && posPonto === -1) {
    normalizado = texto;
  } else if (posVirgula > posPonto) {
    normalizado = texto.replace(/\./g, "").replace(",", ".");
  } else {
    normalizado = texto.replace(/,/g, "");
  }

  if (!/^\d+(\.\d+)?$/.test(normalizado)) {
    throw new Error(`Valor inválido: '${textoOriginal}'.`);
  }

  return negativo ? `-${normalizado}` : normalizado;
}
