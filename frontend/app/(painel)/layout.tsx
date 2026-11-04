import { AppShell } from "@/components/layout/AppShell";

export default function LayoutPainel({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
