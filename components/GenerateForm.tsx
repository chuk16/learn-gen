"use client";

import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Loader2Icon, Settings2Icon } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger
} from "@/components/ui/sheet";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { getApiBaseUrl } from "@/lib/config";
import {
  generateFormSchema,
  type GenerateFormValues
} from "@/lib/validators";

const LENGTH_OPTIONS = [
  { label: "30 seconds", value: "30" },
  { label: "60 seconds", value: "60" },
  { label: "90 seconds", value: "90" }
] as const;

const ASPECT_OPTIONS = [
  { label: "Portrait", value: "portrait" },
  { label: "Landscape", value: "landscape" },
  { label: "Square", value: "square" }
] as const;

const DEFAULTS = {
  voicePath: "/workspace/learn-gen/voices/piper/en_US-lessac-high.onnx",
  portraitHeight: 1920,
  landscapeHeight: 1080
};

const LENGTH_PAYLOAD_MAP = {
  "30": { unit: "sec" as const, value: 30 },
  "60": { unit: "sec" as const, value: 60 },
  "90": { unit: "sec" as const, value: 90 }
};

export type GenerateFormProps = {
  onResult: (payload: unknown) => void;
  onSubmittingChange?: (pending: boolean) => void;
};

type SubmitState = "idle" | "submitting" | "error";

export default function GenerateForm({
  onResult,
  onSubmittingChange
}: GenerateFormProps) {
  const [submitState, setSubmitState] = useState<SubmitState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const form = useForm<GenerateFormValues>({
    resolver: zodResolver(generateFormSchema),
    defaultValues: {
      topic: "",
      length: "60",
      aspect: "portrait",
      targetHeight: DEFAULTS.portraitHeight,
      voicePath: DEFAULTS.voicePath,
      paceWpm: 150,
      webSearch: false
    }
  });

  const aspect = form.watch("aspect");
  const targetHeightDirty = form.formState.dirtyFields?.targetHeight ?? false;

  useEffect(() => {
    const autoHeight =
      aspect === "portrait" ? DEFAULTS.portraitHeight : DEFAULTS.landscapeHeight;
    if (!targetHeightDirty) {
      form.setValue("targetHeight", autoHeight, {
        shouldDirty: false,
        shouldValidate: false
      });
    }
  }, [aspect, form, targetHeightDirty]);

  useEffect(() => {
    onSubmittingChange?.(submitState === "submitting");
  }, [submitState, onSubmittingChange]);

  async function onSubmit(values: GenerateFormValues) {
    setErrorMessage(null);
    setSubmitState("submitting");

    const cleanedTopic = values.topic.trim();
    const payload = {
      topic: cleanedTopic,
      length: LENGTH_PAYLOAD_MAP[values.length],
      research: {
        web_search: values.webSearch,
        sources: [] as string[]
      },
      visuals: {
        use_generated_images: "none",
        style: "minimal-3D|flat-vector",
        fps: 30,
        animation_mode: "cinematic",
        aspect: values.aspect,
        target_height: values.targetHeight
      },
      voice: {
        speaker: values.voicePath,
        pace_wpm: values.paceWpm,
        tone: "energetic"
      },
      structure: {
        beats_per_min: 10,
        cta: false,
        quizlets: 0
      }
    };

    try {
      const response = await fetch(`${getApiBaseUrl()}/v1/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const message = await safeParseError(response);
        throw new Error(message);
      }

      const data = (await response.json()) as unknown;
      onResult(data);
      form.reset({
        ...values,
        topic: cleanedTopic
      });
      setSubmitState("idle");
    } catch (error) {
      console.error(error);
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Something went wrong. Please try again."
      );
      setSubmitState("error");
    }
  }

  return (
    <Form {...form}>
      <form className="space-y-8" onSubmit={form.handleSubmit(onSubmit)}>
        <div className="space-y-6">
          <FormField
            control={form.control}
            name="topic"
            render={({ field }) => (
              <FormItem>
                <FormLabel>What video should we make?</FormLabel>
                <FormControl>
                  <Textarea
                    placeholder="Explain the science behind Interstellar in 1 minute…"
                    {...field}
                  />
                </FormControl>
                <FormDescription>
                  Provide context, target audience, and key beats you want covered.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              control={form.control}
              name="length"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Length</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select length" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {LENGTH_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>Choose the target runtime.</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="aspect"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Aspect</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select aspect" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {ASPECT_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    Portrait favors mobile, landscape suits widescreen playback.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        </div>

        <Sheet>
          <SheetTrigger asChild>
            <Button type="button" variant="outline">
              <Settings2Icon className="mr-2 h-4 w-4" />
              Advanced options
            </Button>
          </SheetTrigger>
          <SheetContent>
            <SheetHeader>
              <SheetTitle>Advanced controls</SheetTitle>
              <SheetDescription>
                Fine-tune render settings, narration, and optional research.
              </SheetDescription>
            </SheetHeader>

            <div className="space-y-6">
              <FormField
                control={form.control}
                name="targetHeight"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Target height (px)</FormLabel>
                    <FormControl>
                      <Input
                        inputMode="numeric"
                        min={480}
                        step={10}
                        type="number"
                        {...field}
                        value={field.value ?? ""}
                      />
                    </FormControl>
                    <FormDescription>
                      Defaults to 1920 for portrait; 1080 for landscape or square.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="voicePath"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Voice model path</FormLabel>
                    <FormControl>
                      <Input placeholder={DEFAULTS.voicePath} {...field} />
                    </FormControl>
                    <FormDescription>
                      Provide an absolute path reachable by the backend runtime.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="paceWpm"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Pace (words per minute)</FormLabel>
                    <FormControl>
                      <Input
                        inputMode="numeric"
                        min={80}
                        max={240}
                        type="number"
                        {...field}
                        value={field.value ?? ""}
                      />
                    </FormControl>
                    <FormDescription>
                      Lower numbers for deliberate reads, higher for energetic deliveries.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="webSearch"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between rounded-2xl border border-slate-200 bg-slate-50/70 px-4 py-3">
                    <div className="space-y-0.5">
                      <FormLabel className="text-sm font-semibold text-slate-800">
                        Web search
                      </FormLabel>
                      <FormDescription>
                        Enable to pull supporting facts before scripting.
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                  </FormItem>
                )}
              />
            </div>
          </SheetContent>
        </Sheet>

        {errorMessage ? (
          <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
            {errorMessage}
          </p>
        ) : null}

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-slate-500">
            Tip: Save preferred defaults; advanced settings persist until refreshed.
          </p>
          <Button
            className="min-w-[160px]"
            disabled={submitState === "submitting"}
            size="lg"
            type="submit"
          >
            {submitState === "submitting" ? (
              <span className="flex items-center gap-2">
                <Loader2Icon className="h-4 w-4 animate-spin" />
                Generating…
              </span>
            ) : (
              "Generate"
            )}
          </Button>
        </div>
      </form>
    </Form>
  );
}

async function safeParseError(response: Response) {
  try {
    const data = await response.json();
    if (typeof data === "object" && data && "detail" in data) {
      return Array.isArray(data.detail)
        ? data.detail.join(", ")
        : String(data.detail);
    }
    return JSON.stringify(data);
  } catch {
    return `${response.status} ${response.statusText}`;
  }
}
