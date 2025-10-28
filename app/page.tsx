"use client";

import { useState } from "react";
import { Loader2Icon, SparklesIcon } from "lucide-react";

import GenerateForm from "@/components/GenerateForm";
import ResultsPanel from "@/components/ResultsPanel";

import { Card } from "@/components/ui/card";

type GenerateResponse = {
  status?: string;
  outputs?: string[];
  data?: unknown;
  url?: string;
  [key: string]: unknown;
};

export default function HomePage() {
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  return (
    <main className="min-h-screen w-full bg-[radial-gradient(circle_at_top,_rgba(191,219,254,0.35)_0%,_rgba(255,255,255,0.9)_45%,_rgba(255,255,255,1)_100%)]">
      <div className="w-full bg-accent-gradient py-6 shadow-sm">
        <div className="container flex max-w-4xl flex-col gap-4 px-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-lg font-semibold tracking-tight text-slate-800 sm:text-xl">
                Learn Gen
              </p>
              <p className="text-sm text-slate-600">
                Modern interface for orchestrating AI-driven video generation.
              </p>
            </div>
            <div className="hidden sm:flex items-center gap-2 rounded-full bg-white/60 px-4 py-2 text-sm text-slate-600 shadow-inner">
              <SparklesIcon className="h-4 w-4 text-sky-500" />
              <span>Tell a story, we&apos;ll bring it to life.</span>
            </div>
          </div>
        </div>
      </div>

      <div className="container relative z-10 -mt-10 max-w-4xl space-y-8 pb-16">
        <Card className="glass w-full rounded-3xl px-6 py-8 shadow-xl">
          <div className="mb-6 flex flex-col gap-2">
            <h1 className="text-2xl font-semibold text-slate-900 sm:text-3xl">
              Plan your next video.
            </h1>
            <p className="text-sm text-slate-600 sm:text-base">
              Describe the video, set the basics, tweak advanced options, and
              let Learn Gen orchestrate the rest.
            </p>
          </div>

          <GenerateForm
            onResult={(payload) => setResult(payload)}
            onSubmittingChange={setIsSubmitting}
          />
        </Card>

        <Card className="glass w-full rounded-3xl px-6 py-6 shadow-xl">
          <div className="mb-4 flex items-center justify-between gap-2">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">
                Results
              </h2>
              <p className="text-sm text-slate-600">
                Preview generated videos or copy paths for remote retrieval.
              </p>
            </div>
            {isSubmitting && (
              <div className="flex items-center gap-2 rounded-full bg-white/70 px-3 py-1 text-xs font-medium text-slate-600 shadow-inner">
                <Loader2Icon className="h-4 w-4 animate-spin text-sky-500" />
                Generating…
              </div>
            )}
          </div>

          <ResultsPanel result={result} />
        </Card>
      </div>

      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_20%_20%,rgba(125,211,252,0.25),transparent_55%)]" />
      <div className="pointer-events-none absolute inset-0 -z-20 bg-[radial-gradient(circle_at_80%_10%,rgba(199,210,254,0.35),transparent_50%)]" />
    </main>
  );
}
