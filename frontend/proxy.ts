import { type NextRequest } from "next/server";

import { atualizarSessao } from "@/lib/supabase/middleware";

export async function proxy(request: NextRequest) {
  return atualizarSessao(request);
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|manifest.json|sw\\.js|icons|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
