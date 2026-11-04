import { ReactNode } from "react";

export type Coluna<T> = {
  chave: string;
  titulo: string;
  render: (item: T) => ReactNode;
  className?: string;
  ocultarNoCard?: boolean;
};

type Props<T> = {
  itens: T[];
  colunas: Coluna<T>[];
  chaveLinha: (item: T) => string | number;
  corFundoLinha?: (item: T) => string;
  vazio?: ReactNode;
};

/** Tabela em desktop, cards em mobile (Parte 13 — mobile-first, nunca
 * exigir scroll horizontal descontrolado para operações principais). */
export function DataTable<T>({ itens, colunas, chaveLinha, corFundoLinha, vazio }: Props<T>) {
  if (itens.length === 0) return <>{vazio}</>;

  return (
    <>
      <div className="hidden overflow-x-auto rounded-xl border border-borda sm:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-borda text-left text-muted">
              {colunas.map((coluna) => (
                <th key={coluna.chave} className="px-3 py-2 font-medium">
                  {coluna.titulo}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {itens.map((item) => (
              <tr
                key={chaveLinha(item)}
                className={`border-b border-borda last:border-0 ${corFundoLinha?.(item) ?? ""}`}
              >
                {colunas.map((coluna) => (
                  <td key={coluna.chave} className={`px-3 py-2 ${coluna.className ?? ""}`}>
                    {coluna.render(item)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-2 sm:hidden">
        {itens.map((item) => (
          <div
            key={chaveLinha(item)}
            className={`rounded-xl border border-borda p-3 ${corFundoLinha?.(item) ?? ""}`}
          >
            {colunas
              .filter((c) => !c.ocultarNoCard)
              .map((coluna) => (
                <div key={coluna.chave} className="flex items-center justify-between gap-2 py-0.5 text-sm">
                  <span className="text-muted">{coluna.titulo}</span>
                  <span className="text-right text-foreground">{coluna.render(item)}</span>
                </div>
              ))}
          </div>
        ))}
      </div>
    </>
  );
}
