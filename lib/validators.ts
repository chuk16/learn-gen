import { z } from "zod";

export const generateFormSchema = z.object({
  topic: z
    .string()
    .min(3, "Tell us what video to make.")
    .max(500, "Let's keep it under 500 characters."),
  length: z.enum(["30", "60", "90"], {
    errorMap: () => ({ message: "Choose a length." })
  }),
  aspect: z.enum(["portrait", "landscape", "square"], {
    errorMap: () => ({ message: "Select an aspect ratio." })
  }),
  targetHeight: z.coerce
    .number({
      invalid_type_error: "Enter a number."
    })
    .int("Use whole pixels.")
    .min(480, "Minimum height is 480.")
    .max(4320, "Maximum height is 4320."),
  voicePath: z
    .string()
    .min(1, "Provide the voice model path.")
    .max(400, "Keep the path under 400 characters."),
  paceWpm: z.coerce
    .number({
      invalid_type_error: "Enter a number."
    })
    .int("Use a whole number.")
    .min(80, "Minimum is 80 WPM.")
    .max(240, "Maximum is 240 WPM."),
  webSearch: z.boolean()
});

export type GenerateFormValues = z.infer<typeof generateFormSchema>;
