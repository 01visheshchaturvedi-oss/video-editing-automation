"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Play, Folder, Music, Video, Loader2, FileTerminal, CheckCircle2, AlertCircle } from "lucide-react";

export default function Home() {
  const [mediaDir, setMediaDir] = useState("/workspaces/video-editing-automation/backend");
  const [audioFile, setAudioFile] = useState("/workspaces/video-editing-automation/backend/haldi_mashup.mp3");
  const [outputFile, setOutputFile] = useState("/workspaces/video-editing-automation/backend/video.mp4");

  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<"idle" | "running" | "success" | "error">("idle");
  const [logs, setLogs] = useState<string[]>([]);

  const terminalRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of terminal
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mediaDir || !audioFile || !outputFile) return;

    setIsLoading(true);
    setStatus("running");
    setLogs(["[V-AUTO] Starting video generation engine...", `[V-AUTO] Target: ${outputFile}`]);

    try {
      const response = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mediaDir, audioFile, outputFile }),
      });

      if (!response.body) {
        throw new Error("ReadableStream not supported in this browser.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n").filter(line => line.trim() !== "");
          setLogs(prev => [...prev, ...lines]);

          if (chunk.includes("[COMPLETED]")) {
            setStatus("success");
          } else if (chunk.includes("FATAL ERROR") || chunk.includes("Process exited with error code") || chunk.includes("Spawn Error:")) {
            setStatus("error");
          }
        }
      }
    } catch (err: any) {
      setLogs(prev => [...prev, `[NETWORK ERROR] ${err.message}`]);
      setStatus("error");
    } finally {
      setIsLoading(false);
      // Only mark success if we haven't already set an error status mid-stream
      setStatus(prev => (prev === "error" || prev === "success") ? prev : "idle");
    }
  };

  return (
    <main className="min-h-screen py-12 px-4 sm:px-6 lg:px-8 flex flex-col items-center justify-center">
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-[#0a0f1c] to-black opacity-90"></div>

      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-5xl text-center mb-10"
      >
        <h1 className="text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400 tracking-tight sm:text-6xl mb-4">
          Automated Video Editor
        </h1>
        <p className="mt-4 text-lg text-slate-300 max-w-2xl mx-auto font-light">
          A high-performance pipeline that intuitively cuts, polishes, and syncs your photos and videos perfectly to the beat.
        </p>
      </motion.div>

      <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Side: Configuration Form */}
        <motion.div
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="lg:col-span-5 bg-white/5 backdrop-blur-xl border border-white/10 p-8 rounded-3xl shadow-[0_0_40px_rgba(4,159,108,0.15)] relative overflow-hidden group"
        >
          {/* Subtle gradient glow behind the card */}
          <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-3xl blur opacity-0 group-hover:opacity-20 transition duration-1000 -z-10"></div>

          <h2 className="text-2xl font-bold text-white mb-6 flex items-center">
            <span className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center mr-3">
              <Folder size={18} />
            </span>
            Configuration
          </h2>

          <form onSubmit={handleGenerate} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Media Directory</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Folder size={18} />
                </div>
                <input
                  type="text"
                  value={mediaDir}
                  onChange={(e) => setMediaDir(e.target.value)}
                  className="block w-full pl-10 pr-3 py-3 border border-white/10 rounded-xl bg-black/40 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all font-mono text-sm"
                  placeholder="C:\path\to\folder"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Audio File</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Music size={18} />
                </div>
                <input
                  type="text"
                  value={audioFile}
                  onChange={(e) => setAudioFile(e.target.value)}
                  className="block w-full pl-10 pr-3 py-3 border border-white/10 rounded-xl bg-black/40 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all font-mono text-sm"
                  placeholder="C:\path\to\audio.mp3"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Output Video Path</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Video size={18} />
                </div>
                <input
                  type="text"
                  value={outputFile}
                  onChange={(e) => setOutputFile(e.target.value)}
                  className="block w-full pl-10 pr-3 py-3 border border-white/10 rounded-xl bg-black/40 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all font-mono text-sm"
                  placeholder="C:\path\to\video.mp4"
                  required
                />
              </div>
            </div>

            <div className="pt-4">
              <motion.button
                whileHover={{ scale: isLoading ? 1 : 1.02 }}
                whileTap={{ scale: isLoading ? 1 : 0.98 }}
                type="submit"
                disabled={isLoading}
                className={`w-full flex justify-center items-center py-4 px-4 border border-transparent rounded-xl shadow-lg text-base font-medium text-white transition-all
                  ${isLoading
                    ? 'bg-slate-700 cursor-not-allowed'
                    : 'bg-gradient-to-r from-emerald-500 to-cyan-600 hover:from-emerald-400 hover:to-cyan-500'
                  }`}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" />
                    Processing Pipeline...
                  </>
                ) : (
                  <>
                    <Play className="-ml-1 mr-2 h-5 w-5" />
                    Generate Masterpiece
                  </>
                )}
              </motion.button>
            </div>
          </form>
        </motion.div>

        {/* Right Side: Terminal / Logs */}
        <motion.div
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="lg:col-span-7 bg-[#0a0c10] border border-white/10 rounded-3xl shadow-2xl flex flex-col overflow-hidden"
        >
          {/* Mac-like Terminal Header */}
          <div className="bg-[#161b22] px-4 py-3 border-b border-white/5 flex items-center justify-between">
            <div className="flex space-x-2">
              <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
              <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
              <div className="w-3 h-3 rounded-full bg-green-500/80"></div>
            </div>
            <div className="flex items-center text-xs text-slate-400 font-mono">
              <FileTerminal size={12} className="mr-2" />
              V-AUTO ENGINE
            </div>
            <div></div>
          </div>

          <div
            ref={terminalRef}
            className="flex-1 p-6 overflow-y-auto font-mono text-xs sm:text-sm text-emerald-400 leading-relaxed min-h-[400px]"
            style={{ maxHeight: '600px' }}
          >
            {logs.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-500 opacity-50 space-y-4">
                <FileTerminal size={48} />
                <p>Awaiting engine start command...</p>
              </div>
            ) : (
              <div className="space-y-1">
                {logs.map((log, index) => {
                  let textColor = "text-emerald-400";
                  if (log.toLowerCase().includes("error") || log.toLowerCase().includes("failed")) textColor = "text-red-400";
                  if (log.toLowerCase().includes("phase")) textColor = "text-cyan-400 font-bold mt-4 border-l-2 border-cyan-400 pl-2";
                  if (log.includes("[COMPLETED]")) textColor = "text-green-400 font-black mt-4";

                  return (
                    <div key={index} className={`break-all ${textColor}`}>
                      <span className="text-slate-600 mr-2 opacity-50">{String(index + 1).padStart(3, '0')}</span>
                      {log}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Status Footer */}
          <div className="bg-[#0d1117] border-t border-white/5 px-6 py-4 flex items-center justify-between">
            <div className="flex items-center">
              {status === "idle" && <div className="text-slate-500 text-sm flex items-center"><span className="w-2 h-2 rounded-full bg-slate-500 mr-2"></span> System Ready</div>}
              {status === "running" && <div className="text-emerald-500 text-sm flex items-center animate-pulse"><span className="w-2 h-2 rounded-full bg-emerald-500 mr-2"></span> Engine Active: Rendering</div>}
              {status === "success" && <div className="text-green-400 text-sm flex items-center"><CheckCircle2 size={16} className="mr-2" /> Output Generated Successfully</div>}
              {status === "error" && <div className="text-red-400 text-sm flex items-center"><AlertCircle size={16} className="mr-2" /> Automation Pipeline Failed</div>}
            </div>

            {status === "running" && (
              <div className="flex space-x-1">
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce"></div>
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </main>
  );
}
