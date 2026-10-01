import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/page-header";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export const metadata: Metadata = { title: "Sources" };

export default function SourcesPage() {
  return (
    <>
      <PageHeader title="Sources" description="Your library of channels, videos and transcripts." />
      <div className="grid gap-4 sm:grid-cols-2">
        <Link href="/sources/channels">
          <Card className="hover:bg-accent/40">
            <CardHeader>
              <CardTitle>Channels</CardTitle>
              <CardDescription>Imported YouTube channels and their video counts.</CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link href="/sources/videos">
          <Card className="hover:bg-accent/40">
            <CardHeader>
              <CardTitle>Videos</CardTitle>
              <CardDescription>Individual source videos and transcript status.</CardDescription>
            </CardHeader>
          </Card>
        </Link>
      </div>
    </>
  );
}
