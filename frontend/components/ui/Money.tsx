import { formatarMoeda } from "@/lib/utils/formatadores";

export function Money({
  valor,
  className = "",
}: {
  valor: number | string | null | undefined;
  className?: string;
}) {
  if (valor === null || valor === undefined) {
    return <span className={className}>—</span>;
  }
  return <span className={className}>{formatarMoeda(valor)}</span>;
}
