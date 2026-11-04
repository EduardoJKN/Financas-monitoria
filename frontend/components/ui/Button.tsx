import { ButtonHTMLAttributes, forwardRef } from "react";

type Variante = "primaria" | "secundaria" | "perigo" | "fantasma";

const CLASSES_VARIANTE: Record<Variante, string> = {
  primaria: "bg-primaria text-primaria-foreground hover:opacity-90",
  secundaria: "bg-superficie text-foreground border border-borda hover:bg-borda/40",
  perigo: "bg-despesa-texto text-white hover:opacity-90",
  fantasma: "bg-transparent text-foreground hover:bg-superficie",
};

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variante?: Variante;
  carregando?: boolean;
};

export const Button = forwardRef<HTMLButtonElement, Props>(
  ({ variante = "primaria", carregando, className = "", children, disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled || carregando}
        aria-busy={carregando}
        className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium
          transition-colors disabled:opacity-50 disabled:cursor-not-allowed
          ${CLASSES_VARIANTE[variante]} ${className}`}
        {...props}
      >
        {carregando && (
          <span
            className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
            aria-hidden="true"
          />
        )}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
