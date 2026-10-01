"use client";

import { useParams } from "next/navigation";
import { SourceDetailView } from "@/components/sources/source-detail";

export default function SourcePage() {
  const { id } = useParams<{ id: string }>();
  return <SourceDetailView id={id} />;
}
