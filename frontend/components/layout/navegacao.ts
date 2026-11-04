import {
  Home,
  LayoutDashboard,
  Receipt,
  Landmark,
  CreditCard,
  Tags,
  Upload,
  Target,
  Calculator,
  Wand2,
  RefreshCw,
  CalendarClock,
  type LucideIcon,
} from "lucide-react";

export type ItemNavegacao = {
  href: string;
  rotulo: string;
  icone: LucideIcon;
};

export const ITENS_NAVEGACAO: ItemNavegacao[] = [
  { href: "/inicio", rotulo: "Início", icone: Home },
  { href: "/visao-geral", rotulo: "Visão Geral", icone: LayoutDashboard },
  { href: "/lancamentos", rotulo: "Lançamentos", icone: Receipt },
  { href: "/contas", rotulo: "Contas", icone: Landmark },
  { href: "/cartoes", rotulo: "Cartões", icone: CreditCard },
  { href: "/categorias", rotulo: "Categorias", icone: Tags },
  { href: "/regras", rotulo: "Regras", icone: Wand2 },
  { href: "/recorrencias", rotulo: "Recorrências", icone: RefreshCw },
  { href: "/importacao", rotulo: "Importação", icone: Upload },
  { href: "/metas", rotulo: "Metas", icone: Target },
  { href: "/simulador", rotulo: "Simulador", icone: Calculator },
  { href: "/compromissos", rotulo: "Compromissos", icone: CalendarClock },
];

// Subconjunto para a barra inferior do mobile — os 5 mais usados; o
// restante fica acessível pelo menu "Mais" (drawer).
export const ITENS_BOTTOM_NAV = [
  ITENS_NAVEGACAO[0],
  ITENS_NAVEGACAO[1],
  ITENS_NAVEGACAO[2],
  ITENS_NAVEGACAO[3],
];
