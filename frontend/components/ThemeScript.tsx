/** Aplica o tema salvo (ou a preferência do sistema) ANTES da hidratação,
 * evitando flash de tema errado. Não lê nem escreve nada sensível — só a
 * preferência de tema em localStorage. */
const SCRIPT = `
(function () {
  try {
    var salvo = localStorage.getItem("tema");
    var sistemaEscuro = window.matchMedia("(prefers-color-scheme: dark)").matches;
    var escuro = salvo === "escuro" || (salvo !== "claro" && sistemaEscuro);
    document.documentElement.classList.toggle("dark", escuro);
    document.documentElement.classList.toggle("light", !escuro);
  } catch (e) {}
})();
`;

export function ThemeScript() {
  return <script dangerouslySetInnerHTML={{ __html: SCRIPT }} />;
}
