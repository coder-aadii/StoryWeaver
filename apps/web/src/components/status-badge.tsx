import { Badge } from "@/components/ui/badge";

type Variant = "default" | "secondary" | "destructive" | "outline";

const VARIANTS: Record<string, Variant> = {
  completed: "default",
  ready: "default",
  imported: "default",
  failed: "destructive",
  draft: "outline",
  pending: "outline",
  discovered: "outline",
  queued: "outline",
};

export function StatusBadge({ status }: { status: string }) {
  return <Badge variant={VARIANTS[status] ?? "secondary"}>{status}</Badge>;
}
