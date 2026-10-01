"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FilePlus2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useRun } from "@/components/sources/use-run";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  addSourceFromTranscript,
  addSourceFromUrl,
  attachTranscript,
  MAX_TRANSCRIPT_BYTES,
  TRANSCRIPT_EXTENSIONS,
  type AddSourceResult,
} from "@/lib/sources-api";

// ---- client-side checks (mirror the server limits; the server remains the authority) ----------

export function validateUrlInput(url: string): string | null {
  const value = url.trim();
  if (!value) return "Enter a YouTube video URL.";
  if (!/^https?:\/\//i.test(value)) return "The URL must start with http:// or https://.";
  return null;
}

export function validateTranscriptInput(input: {
  file: File | null;
  text: string;
  title: string;
  /** Attaching to an existing source: it already has a title, so none is required. */
  attach?: boolean;
}): string | null {
  if (!input.attach) {
    if (!input.title.trim()) return "Give the transcript a title.";
    if (input.title.trim().length > 1024) return "The title is too long (max 1024 characters).";
  }
  if (input.file) {
    const name = input.file.name.toLowerCase();
    if (!TRANSCRIPT_EXTENSIONS.some((ext) => name.endsWith(ext))) {
      return `Unsupported file type. Use ${TRANSCRIPT_EXTENSIONS.join(", ")}.`;
    }
    if (input.file.size === 0) return "The file is empty.";
    if (input.file.size > MAX_TRANSCRIPT_BYTES) {
      return `The file is too large (max ${MAX_TRANSCRIPT_BYTES / (1024 * 1024)} MB).`;
    }
    return null;
  }
  if (!input.text.trim()) return "Choose a file or paste the transcript text.";
  if (new Blob([input.text]).size > MAX_TRANSCRIPT_BYTES) {
    return `The text is too large (max ${MAX_TRANSCRIPT_BYTES / (1024 * 1024)} MB).`;
  }
  return null;
}

// ---- result panel -------------------------------------------------------------------------------

function RunProgress({ result }: { result: AddSourceResult }) {
  const run = useRun(result.run?.id);
  const current = run.data ?? result.run;
  const sourceHref = `/sources/videos/${result.source.id}`;
  if (!current) return null;

  if (current.status === "succeeded") {
    return (
      <p role="status" className="text-sm">
        Added.{" "}
        <Link className="underline" href={sourceHref}>
          Open the source
        </Link>
      </p>
    );
  }
  if (current.status === "failed" || current.status === "interrupted") {
    return (
      <div
        role="alert"
        className="border-destructive/40 text-destructive rounded-md border p-3 text-sm"
      >
        <p className="font-medium">
          {current.error
            ? `${current.error.message} (${current.error.code})`
            : `The import ${current.status}.`}
        </p>
        <p className="mt-1">
          {current.error?.code === "no_captions"
            ? "This video has no captions. Add its transcript with the Upload or paste tab."
            : "You can retry from the source page."}{" "}
          <Link className="underline" href={sourceHref}>
            Open the source
          </Link>
        </p>
      </div>
    );
  }
  const step = typeof current.progress?.step === "string" ? ` (${current.progress.step})` : "";
  return (
    <p role="status" aria-live="polite" className="text-muted-foreground text-sm">
      Importing{step}…
    </p>
  );
}

function ResultPanel({ result }: { result: AddSourceResult }) {
  if (result.already_exists) {
    return (
      <p role="status" className="rounded-md border p-3 text-sm">
        This is already in your library:{" "}
        <Link className="underline" href={`/sources/videos/${result.source.id}`}>
          {result.source.title}
        </Link>
        {result.match === "fingerprint" ? " (same transcript text)" : ""}.
      </p>
    );
  }
  if (result.run) return <RunProgress result={result} />;
  return (
    <p role="status" className="text-sm">
      Added.{" "}
      <Link className="underline" href={`/sources/videos/${result.source.id}`}>
        Open the source
      </Link>
    </p>
  );
}

// ---- dialog -------------------------------------------------------------------------------------

export interface AddSourceDialogProps {
  /**
   * Attach mode: add or replace the transcript of this EXISTING source (the no-captions fallback).
   * Shows only the upload form — no title, no URL tab — and never creates a new source.
   */
  attachToSourceId?: string;
  /** Which tab opens first (ignored in attach mode, which is upload-only). */
  initialTab?: "url" | "upload";
  /** Pre-fill the transcript title (create mode only). */
  initialTitle?: string;
  label?: string;
  variant?: "default" | "outline" | "secondary" | "ghost";
}

export function AddSourceDialog({
  attachToSourceId,
  initialTab = "url",
  initialTitle = "",
  label,
  variant = "default",
}: AddSourceDialogProps) {
  const queryClient = useQueryClient();
  const attach = Boolean(attachToSourceId);
  const buttonLabel = label ?? (attach ? "Upload transcript" : "Add source");
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<string>(attach ? "upload" : initialTab);
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState(initialTitle);
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [language, setLanguage] = useState("");
  const [referenceUrl, setReferenceUrl] = useState("");
  const [clientError, setClientError] = useState<string | null>(null);
  const [result, setResult] = useState<AddSourceResult | null>(null);
  const [attached, setAttached] = useState(false);

  const onSuccess = (r: AddSourceResult) => {
    setResult(r);
    void queryClient.invalidateQueries({ queryKey: ["/sources"] });
  };
  const urlMutation = useMutation({ mutationFn: addSourceFromUrl, onSuccess });
  const uploadMutation = useMutation({ mutationFn: addSourceFromTranscript, onSuccess });
  const attachMutation = useMutation({
    mutationFn: (form: FormData) => attachTranscript(attachToSourceId as string, form),
    onSuccess: () => {
      setAttached(true);
      void queryClient.invalidateQueries({ queryKey: ["/sources", attachToSourceId] });
      void queryClient.invalidateQueries({ queryKey: ["/sources"] });
    },
  });
  const pending = urlMutation.isPending || uploadMutation.isPending || attachMutation.isPending;
  const serverError =
    (attach ? attachMutation.error : tab === "url" ? urlMutation.error : uploadMutation.error)
      ?.message ?? null;

  function reset() {
    setUrl("");
    setTitle(initialTitle);
    setFile(null);
    setText("");
    setLanguage("");
    setReferenceUrl("");
    setClientError(null);
    setResult(null);
    setAttached(false);
    urlMutation.reset();
    uploadMutation.reset();
    attachMutation.reset();
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setResult(null);
    setAttached(false);

    if (attach) {
      const err = validateTranscriptInput({ file, text, title, attach: true });
      setClientError(err);
      if (err) return;
      const form = new FormData();
      if (file) form.append("file", file);
      else form.append("text", text);
      if (language.trim()) form.append("language", language.trim());
      attachMutation.mutate(form);
      return;
    }
    if (tab === "url") {
      const err = validateUrlInput(url);
      setClientError(err);
      if (!err) urlMutation.mutate(url.trim());
      return;
    }
    const err = validateTranscriptInput({ file, text, title });
    setClientError(err);
    if (err) return;
    const form = new FormData();
    if (file) form.append("file", file);
    else form.append("text", text);
    form.append("title", title.trim());
    if (language.trim()) form.append("language", language.trim());
    if (referenceUrl.trim()) form.append("reference_url", referenceUrl.trim());
    uploadMutation.mutate(form);
  }

  const uploadFields = (
    <>
      {!attach && (
        <div className="grid gap-1.5">
          <Label htmlFor="source-title">Title</Label>
          <Input
            id="source-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={1024}
          />
        </div>
      )}
      <div className="grid gap-1.5">
        <Label htmlFor="source-file">Transcript file (.txt, .srt, .vtt — up to 5 MB)</Label>
        <Input
          id="source-file"
          type="file"
          accept={TRANSCRIPT_EXTENSIONS.join(",")}
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="source-text">Or paste text</Label>
        <Textarea
          id="source-text"
          rows={5}
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={Boolean(file)}
        />
      </div>
      <div className={attach ? "grid gap-3" : "grid grid-cols-2 gap-3"}>
        <div className="grid gap-1.5">
          <Label htmlFor="source-language">Language (optional)</Label>
          <Input
            id="source-language"
            placeholder="en"
            maxLength={16}
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          />
        </div>
        {!attach && (
          <div className="grid gap-1.5">
            <Label htmlFor="source-reference">Reference URL (optional)</Label>
            <Input
              id="source-reference"
              value={referenceUrl}
              onChange={(e) => setReferenceUrl(e.target.value)}
            />
          </div>
        )}
      </div>
    </>
  );

  return (
    <>
      <Button variant={variant} onClick={() => setOpen(true)}>
        <FilePlus2 aria-hidden /> {buttonLabel}
      </Button>
      <Dialog
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          if (!next) reset();
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <form onSubmit={submit} className="grid gap-4" noValidate>
            <DialogHeader>
              <DialogTitle>{attach ? "Upload a transcript" : "Add a source"}</DialogTitle>
              <DialogDescription>
                {attach
                  ? "Add or replace this source's transcript (.txt, .srt or .vtt). The source itself is kept; no new source is created."
                  : "Add a YouTube video (metadata and captions only — no video is downloaded) or a transcript you already have."}
              </DialogDescription>
            </DialogHeader>

            {attach ? (
              <div className="grid gap-3">{uploadFields}</div>
            ) : (
              <Tabs
                value={tab}
                onValueChange={(v) => {
                  setTab(String(v));
                  setClientError(null);
                }}
              >
                <TabsList>
                  <TabsTrigger value="url">YouTube URL</TabsTrigger>
                  <TabsTrigger value="upload">Upload or paste</TabsTrigger>
                </TabsList>

                <TabsContent value="url" className="grid gap-2 pt-2">
                  <Label htmlFor="source-url">YouTube video URL</Label>
                  <Input
                    id="source-url"
                    type="url"
                    inputMode="url"
                    placeholder="https://www.youtube.com/watch?v=…"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    aria-invalid={Boolean(clientError) && tab === "url"}
                  />
                  <p className="text-muted-foreground text-xs">
                    Channels and playlists are not supported yet — channel import arrives in a later
                    release.
                  </p>
                </TabsContent>

                <TabsContent value="upload" className="grid gap-3 pt-2">
                  {uploadFields}
                </TabsContent>
              </Tabs>
            )}

            {(clientError || serverError) && (
              <p role="alert" className="text-destructive text-sm">
                {clientError ?? serverError}
              </p>
            )}
            {attached && (
              <p role="status" className="text-sm">
                Transcript added. The source has been updated.
              </p>
            )}
            {result && <ResultPanel result={result} />}

            <DialogFooter>
              <Button type="submit" disabled={pending}>
                {pending
                  ? "Adding…"
                  : attach
                    ? "Add transcript"
                    : tab === "url"
                      ? "Add video"
                      : "Add transcript"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
