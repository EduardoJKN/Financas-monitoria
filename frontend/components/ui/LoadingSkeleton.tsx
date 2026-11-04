export function LoadingSkeleton({ className = "" }: { className?: string }) {
  return (
    <div
      role="status"
      aria-label="Carregando"
      className={`animate-pulse rounded-lg bg-borda/60 ${className}`}
    />
  );
}

export function LoadingCards({ quantidade = 3 }: { quantidade?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: quantidade }).map((_, i) => (
        <LoadingSkeleton key={i} className="h-24" />
      ))}
    </div>
  );
}
