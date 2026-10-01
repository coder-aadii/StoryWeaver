"use client";

import { Suspense } from "react";
import { PageHeader } from "@/components/page-header";
import { SourcesBrowser } from "@/components/sources/sources-browser";
import { LoadingRows } from "@/components/states";

export default function VideosPage() {
  return (
    <>
      <PageHeader
        title="Videos"
        description="Your source library: YouTube videos and transcripts, searchable by keyword."
      />
      {/* useSearchParams needs a Suspense boundary for static prerendering. */}
      <Suspense fallback={<LoadingRows />}>
        <SourcesBrowser />
      </Suspense>
    </>
  );
}
