"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ChevronDownIcon,
  ChevronUpIcon,
  CopyIcon,
  Edit3Icon,
  ExternalLinkIcon,
  ServerIcon,
  VideoIcon
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

type ResultsPanelProps = {
  result: unknown;
};

type MediaEntry = {
  label: string;
  value: string;
  isUrl: boolean;
};

const LOCAL_STORAGE_KEYS = {
  host: "learn-gen:ssh-host",
  port: "learn-gen:ssh-port"
};

export default function ResultsPanel({ result }: ResultsPanelProps) {
  const [showRaw, setShowRaw] = useState(false);
  const [editingSsh, setEditingSsh] = useState(false);
  const [sshHost, setSshHost] = useState("");
  const [sshPort, setSshPort] = useState("");

  useEffect(() => {
    const storedHost = window.localStorage.getItem(LOCAL_STORAGE_KEYS.host);
    const storedPort = window.localStorage.getItem(LOCAL_STORAGE_KEYS.port);
    if (storedHost) {
      setSshHost(storedHost);
    }
    if (storedPort) {
      setSshPort(storedPort);
    }
  }, []);

  const mediaEntries = useMemo(() => extractMediaEntries(result), [result]);
  const firstRemote = mediaEntries.find((entry) => entry.isUrl);
  const firstLocal = mediaEntries.find((entry) => !entry.isUrl);

  const displayHost = sshHost || "<EXTERNAL_IP>";
  const displayPort = sshPort || "<EXTERNAL_SSH_PORT>";

  useEffect(() => {
    if (sshHost) {
      window.localStorage.setItem(LOCAL_STORAGE_KEYS.host, sshHost);
    }
  }, [sshHost]);

  useEffect(() => {
    if (sshPort) {
      window.localStorage.setItem(LOCAL_STORAGE_KEYS.port, sshPort);
    }
  }, [sshPort]);

  if (!result) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-white/70 px-6 py-10 text-center text-sm text-slate-500">
        <p className="mx-auto flex max-w-md flex-col items-center gap-3">
          <VideoIcon className="h-8 w-8 text-slate-400" />
          <span>
            When you generate a video, its status and resulting paths will appear here.
            Remote URLs preview inline; local paths include copy and SCP helpers.
          </span>
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {firstRemote ? (
        <div className="space-y-3 rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm">
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="text-sm font-semibold text-slate-800">
                Preview
              </p>
              <p className="text-xs text-slate-500">{firstRemote.label}</p>
            </div>
            <a
              className="inline-flex items-center gap-1 text-xs font-medium text-sky-600 hover:text-sky-500"
              href={firstRemote.value}
              rel="noopener noreferrer"
              target="_blank"
            >
              Open externally
              <ExternalLinkIcon className="h-3.5 w-3.5" />
            </a>
          </div>
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-900/5">
            <video
              className="aspect-video w-full rounded-2xl bg-black/70"
              controls
              src={firstRemote.value}
            />
          </div>
        </div>
      ) : null}

      {firstLocal ? (
        <div className="space-y-4 rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm">
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="text-sm font-semibold text-slate-800">
                Local artifact
              </p>
              <p className="text-xs text-slate-500">{firstLocal.label}</p>
            </div>
            <div className="flex items-center gap-2">
              <CopyButton value={firstLocal.value} />
              <Button
                onClick={() => setEditingSsh((prev) => !prev)}
                size="sm"
                type="button"
                variant="ghost"
              >
                <Edit3Icon className="mr-1.5 h-4 w-4" />
                {editingSsh ? "Close" : "Edit defaults"}
              </Button>
            </div>
          </div>

          <code className="block w-full overflow-x-auto rounded-xl bg-slate-900/90 px-4 py-3 text-xs text-slate-100">
            {firstLocal.value}
          </code>

          <div className="space-y-2 rounded-2xl bg-slate-50/90 px-4 py-4">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <ServerIcon className="h-4 w-4 text-slate-400" />
              SCP helper
            </p>
            <code className="block overflow-x-auto rounded-xl bg-white px-4 py-3 text-xs font-medium text-slate-800 shadow-inner">
              {`scp -P ${displayPort} root@${displayHost}:${firstLocal.value} .`}
            </code>
          </div>

          {editingSsh ? (
            <div className="grid gap-3 rounded-2xl border border-slate-200 bg-white/80 p-4">
              <div className="grid gap-2 text-left">
                <Label htmlFor="ssh-host">External IP / host</Label>
                <Input
                  id="ssh-host"
                  placeholder="EXTERNAL_IP"
                  value={sshHost}
                  onChange={(event) => setSshHost(event.target.value)}
                />
              </div>
              <div className="grid gap-2 text-left">
                <Label htmlFor="ssh-port">SSH port</Label>
                <Input
                  id="ssh-port"
                  placeholder="EXTERNAL_SSH_PORT"
                  value={sshPort}
                  onChange={(event) => setSshPort(event.target.value)}
                />
              </div>
              <p className="text-xs text-slate-500">
                These values persist in local storage for quick reuse.
              </p>
            </div>
          ) : null}
        </div>
      ) : null}

      {mediaEntries.length > 0 ? (
        <div className="space-y-3 rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm">
          <p className="text-sm font-semibold text-slate-800">Detected media targets</p>
          <ul className="space-y-2 text-xs text-slate-600">
            {mediaEntries.map((entry) => (
              <li
                key={`${entry.label}-${entry.value}`}
                className={cn(
                  "flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2",
                  entry.isUrl ? "text-sky-700" : "text-slate-700"
                )}
              >
                <span className="truncate">
                  <span className="font-medium text-slate-500">{entry.label}:</span>{" "}
                  {entry.value}
                </span>
                <CopyButton value={entry.value} />
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="rounded-2xl border border-dashed border-slate-200 bg-white/60 px-4 py-3 text-xs text-slate-500">
          No media paths detected yet. Review the raw response for more details.
        </p>
      )}

      <div className="space-y-2 rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm">
        <button
          className="flex w-full items-center justify-between gap-2 text-sm font-semibold text-slate-700"
          onClick={() => setShowRaw((prev) => !prev)}
          type="button"
        >
          <span>Raw response</span>
          {showRaw ? (
            <ChevronUpIcon className="h-4 w-4" />
          ) : (
            <ChevronDownIcon className="h-4 w-4" />
          )}
        </button>
        {showRaw ? (
          <pre className="scrollbar-thin max-h-80 overflow-auto rounded-xl bg-slate-950/95 px-4 py-4 text-xs text-slate-100">
            {JSON.stringify(result, null, 2)}
          </pre>
        ) : null}
      </div>
    </div>
  );
}

function extractMediaEntries(source: unknown, prefix = "response"): MediaEntry[] {
  const results: MediaEntry[] = [];

  if (!source || typeof source !== "object") {
    return results;
  }

  const walk = (value: unknown, path: string) => {
    if (typeof value === "string") {
      if (/\.(mp4|mov|webm)$/i.test(value)) {
        results.push({
          label: path,
          value,
          isUrl: /^https?:\/\//i.test(value)
        });
      }
      return;
    }

    if (Array.isArray(value)) {
      value.forEach((item, index) => walk(item, `${path}[${index}]`));
      return;
    }

    if (value && typeof value === "object") {
      Object.entries(value).forEach(([key, nested]) =>
        walk(nested, `${path}.${key}`)
      );
    }
  };

  walk(source, prefix);
  return results;
}

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch (error) {
      console.error("Clipboard copy failed:", error);
    }
  }

  return (
    <Button
      aria-label="Copy value"
      className="shrink-0"
      onClick={handleCopy}
      size="sm"
      type="button"
      variant={copied ? "secondary" : "outline"}
    >
      <CopyIcon className="mr-1.5 h-4 w-4" />
      {copied ? "Copied" : "Copy"}
    </Button>
  );
}
