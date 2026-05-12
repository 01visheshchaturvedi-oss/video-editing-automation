import { NextRequest } from "next/server";
import { spawn, SpawnOptions } from "child_process";
import path from "path";

// Try different Python executable names (cross-platform)
const PYTHON_CANDIDATES = ["/home/codespace/miniconda3/envs/video-editor/bin/python"];

function spawnPython(
  args: string[],
  options: SpawnOptions,
  onData: (text: string) => void,
  onClose: (code: number | null) => void,
  onError: (err: Error) => void,
  candidates = PYTHON_CANDIDATES.slice()
) {
  const exe = candidates.shift();
  if (!exe) {
    onError(new Error("Could not find a valid Python executable (tried: python, python3, py). Please ensure Python is installed and on your PATH."));
    return;
  }

  const proc = spawn(exe, args, options);

  proc.stdout?.on("data", (data: Buffer) => onData(data.toString()));
  proc.stderr?.on("data", (data: Buffer) => onData(`ERROR: ${data.toString()}`));
  proc.on("close", onClose);
  proc.on("error", (err: NodeJS.ErrnoException) => {
    if (err.code === "ENOENT" && candidates.length > 0) {
      // Try next candidate
      spawnPython(args, options, onData, onClose, onError, candidates);
    } else {
      onError(err);
    }
  });
}

export async function POST(req: NextRequest) {
  try {
    const { mediaDir, audioFile, outputFile } = await req.json();

    if (!mediaDir || !audioFile || !outputFile) {
      return new Response(JSON.stringify({ error: "Missing parameters" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    const scriptPath = path.resolve(process.cwd(), "backend", "auto_editor.py");
    const encoder = new TextEncoder();

    const stream = new ReadableStream({
      start(controller) {
        const args = [
          scriptPath,
          "--media_dir", mediaDir,
          "--audio_file", audioFile,
          "--output_file", outputFile,
        ];

        spawnPython(
          args,
          { stdio: ["ignore", "pipe", "pipe"] },
          (text) => {
            try { controller.enqueue(encoder.encode(text)); } catch {}
          },
          (code) => {
            try {
              if (code === 0) {
                controller.enqueue(encoder.encode("\n[COMPLETED]\n"));
              } else {
                controller.enqueue(encoder.encode(`\n[Process exited with error code ${code}]\n`));
              }
              controller.close();
            } catch {}
          },
          (err) => {
            try {
              controller.enqueue(encoder.encode(`\n[Spawn Error: ${err.message}]\n`));
              controller.close();
            } catch {}
          }
        );
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "Transfer-Encoding": "chunked",
      },
    });
  } catch (error: any) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
