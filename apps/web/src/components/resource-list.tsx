"use client";

import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";

export interface Column<T> {
  header: string;
  cell: (row: T) => ReactNode;
}

export function ResourceList<T extends { id: string }>({
  path,
  columns,
  emptyTitle,
  emptyHint,
}: {
  path: string;
  columns: Column<T>[];
  emptyTitle: string;
  emptyHint?: string;
}) {
  const { data, error, isPending } = useQuery({ queryKey: [path], queryFn: () => api<T[]>(path) });

  if (isPending) return <LoadingRows />;
  if (error) return <ErrorState message={error.message} />;
  if (data.length === 0) return <EmptyState title={emptyTitle} hint={emptyHint} />;

  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((c) => (
              <TableHead key={c.header}>{c.header}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((row) => (
            <TableRow key={row.id}>
              {columns.map((c) => (
                <TableCell key={c.header}>{c.cell(row)}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
