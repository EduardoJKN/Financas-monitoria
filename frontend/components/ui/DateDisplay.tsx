import { formatarData } from "@/lib/utils/formatadores";

export function DateDisplay({ valor }: { valor: string | null | undefined }) {
  return <time dateTime={valor ?? undefined}>{formatarData(valor)}</time>;
}
