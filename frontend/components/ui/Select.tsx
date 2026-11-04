import { SelectHTMLAttributes, forwardRef, useId } from "react";

type Opcao = { valor: string; rotulo: string };

type Props = Omit<SelectHTMLAttributes<HTMLSelectElement>, "children"> & {
  rotulo: string;
  opcoes: Opcao[];
  erro?: string;
};

export const Select = forwardRef<HTMLSelectElement, Props>(
  ({ rotulo, opcoes, erro, id, className = "", ...props }, ref) => {
    const idGerado = useId();
    const idFinal = id ?? idGerado;

    return (
      <div className="flex flex-col gap-1">
        <label htmlFor={idFinal} className="text-sm font-medium text-foreground">
          {rotulo}
        </label>
        <select
          ref={ref}
          id={idFinal}
          aria-invalid={!!erro}
          className={`rounded-lg border px-3 py-2 text-sm bg-background text-foreground
            border-borda focus-visible:border-primaria ${erro ? "border-despesa-texto" : ""} ${className}`}
          {...props}
        >
          {opcoes.map((opcao) => (
            <option key={opcao.valor} value={opcao.valor}>
              {opcao.rotulo}
            </option>
          ))}
        </select>
        {erro && (
          <span role="alert" className="text-xs text-despesa-texto">
            {erro}
          </span>
        )}
      </div>
    );
  }
);
Select.displayName = "Select";
