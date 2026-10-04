"use client";

import React, { useState, useRef, DragEvent, ChangeEvent } from "react";

export interface FileDropzoneProps {
  kind: string;
  onFile: (file: File) => void;
  accept?: string;
  busy?: boolean;
  hint?: string;
  className?: string;
}

export default function FileDropzone({
  kind,
  onFile,
  accept = ".csv,text/csv",
  busy = false,
  hint = "Drag & drop your CSV file here, or browse files",
  className = "",
}: FileDropzoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<{ name: string; size: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!busy) setIsDragOver(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (busy) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      setSelectedFile({ name: file.name, size: formatFileSize(file.size) });
      onFile(file);
    }
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelectedFile({ name: file.name, size: formatFileSize(file.size) });
      onFile(file);
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`relative rounded-2xl border-2 border-dashed transition-all p-8 flex flex-col items-center justify-center text-center gap-4 ${
        isDragOver
          ? "border-teal-400 bg-teal-500/10 scale-[1.01]"
          : "border-white/15 bg-white/[0.02] hover:border-white/30"
      } ${busy ? "opacity-60 pointer-events-none" : ""} ${className}`}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleChange}
        className="sr-only"
        id={`file-upload-${kind}`}
      />

      <div className="w-12 h-12 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-2xl text-slate-300">
        File
      </div>

      <div className="space-y-1">
        <label
          htmlFor={`file-upload-${kind}`}
          className="text-sm font-semibold text-indigo-400 hover:text-indigo-300 cursor-pointer underline underline-offset-4 focus-within:ring-2 focus-within:ring-indigo-400 rounded"
        >
          <span>Choose {kind} file</span>
        </label>
        <p className="text-xs text-slate-400 max-w-sm">{hint}</p>
      </div>

      {selectedFile && (
        <div className="mt-2 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-xs text-slate-200">
          <span className="font-medium truncate max-w-[200px]">{selectedFile.name}</span>
          <span className="text-slate-400 font-mono">({selectedFile.size})</span>
          <span className="text-emerald-400 ml-1">✓ Loaded</span>
        </div>
      )}

      {busy && (
        <div className="flex items-center gap-2 text-xs font-medium text-teal-300">
          <div className="w-3.5 h-3.5 rounded-full border-2 border-teal-300 border-t-transparent animate-spin" />
          <span>Processing upload...</span>
        </div>
      )}
    </div>
  );
}
