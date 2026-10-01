"use client";

import {
  BasicComposition,
  sampleTimeline,
  timelineDurationInFrames,
  timelineSchema,
} from "@storyweaver/video";
import { Player } from "@remotion/player";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const timeline = timelineSchema.parse(sampleTimeline);

const PIPELINE = [
  "Project",
  "Timeline JSON",
  "Remotion composition",
  "FFmpeg / Remotion renderer",
  "MP4",
];

export default function StudioPage() {
  return (
    <>
      <PageHeader
        title="Studio"
        description="Placeholder. The full editor is not built; this shows the intended architecture with a sample timeline."
      />
      <div className="grid gap-6 xl:grid-cols-[2fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Preview</CardTitle>
            <CardDescription>
              Sample timeline rendered live by the Remotion Player (placeholder images).
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-hidden rounded-lg border">
              <Player
                component={BasicComposition}
                inputProps={timeline}
                durationInFrames={timelineDurationInFrames(timeline)}
                fps={timeline.fps}
                compositionWidth={timeline.width}
                compositionHeight={timeline.height}
                controls
                style={{ width: "100%" }}
              />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Render path</CardTitle>
            <CardDescription>AI decides content; code decides timing and encoding.</CardDescription>
          </CardHeader>
          <CardContent>
            <ol className="flex flex-col gap-2 text-sm">
              {PIPELINE.map((step, i) => (
                <li key={step} className="flex items-center gap-2">
                  <span className="bg-muted flex size-6 items-center justify-center rounded-full text-xs">
                    {i + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
