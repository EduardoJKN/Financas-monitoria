import { InputHTMLAttributes, forwardRef, useId } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  rotulo: string;
  erro?: string;
  dica?: string;
};

/** Sempre com <label> associado (Parte 29 — formulários acessíveis). */
export const Input = forwardRef<HTMLInputElement, Props>(
  ({ rotulo, erro, dica, id, className = "", ...props }, ref) => {
    const idGerado = useId();
    const idFinal = id ?? idGerado;
    const idErro = erro ? `${idFinal}-erro` : undefined;
    const idDica = dica ? `${idFinal}-dica` : undefined;

    return (
      <div className="flex flex-col gap-1">
        <label htmlFor={idFinal} className="text-sm font-medium text-foreground">
          {rotulo}
        </label>
        <input
          ref={ref}
          id={idFinal}
          aria-invalid={!!erro}
          aria-describedby={[idErro, idDica].filter(Boolean).join(" ") || undefined}
          className={`rounded-lg border px-3 py-2 text-sm bg-background text-foreground
            border-borda focus-visible:border-primaria disabled:opacity-50 ${
              erro ? "border-despesa-texto" : ""
            } ${className}`}
          {...props}
        />
        {dica && (
          <span id={idDica} className="text-xs text-muted">
            {dica}
          </span>
        )}
        {erro && (
          <span id={idErro} role="alert" className="text-xs text-despesa-texto">
            {erro}
          </span>
        )}
      </div>
    );
  }
);
Input.displayName = "Input";
