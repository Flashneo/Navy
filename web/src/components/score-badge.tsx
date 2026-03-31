import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function ScoreBadge({ score }: { score: number }) {
  const variant =
    score >= 0.8
      ? "default"
      : score >= 0.6
      ? "secondary"
      : score >= 0.4
      ? "outline"
      : "destructive";

  const colorClass =
    score >= 0.8
      ? "bg-emerald-500/15 text-emerald-700 border-emerald-500/20"
      : score >= 0.6
      ? "bg-blue-500/15 text-blue-700 border-blue-500/20"
      : score >= 0.4
      ? "bg-amber-500/15 text-amber-700 border-amber-500/20"
      : "bg-red-500/15 text-red-700 border-red-500/20";

  return (
    <Badge variant="outline" className={cn("font-mono text-xs", colorClass)}>
      {(score * 100).toFixed(0)}%
    </Badge>
  );
}
