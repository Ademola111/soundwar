import { motion } from "framer-motion";
import { useState } from "react";
import { Upload, Music, FileAudio, Check, AlertCircle } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

const Submit = () => {
  const [file, setFile] = useState<File | null>(null);
  const [formData, setFormData] = useState({
    title: "",
    description: "",
  });
  const [isDragging, setIsDragging] = useState(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type === "audio/mpeg") {
      setFile(droppedFile);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Will be connected to backend later
    console.log("Submit data:", { file, ...formData });
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="pt-24 pb-20">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-2xl mx-auto"
          >
            {/* Header */}
            <div className="text-center mb-8">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/20 text-primary mb-6">
                <Upload className="w-4 h-4" />
                <span className="text-sm font-semibold">Submit Your Track</span>
              </div>
              <h1 className="font-display text-3xl md:text-4xl font-bold mb-4">
                Upload Your <span className="text-gradient-primary">Song</span>
              </h1>
              <p className="text-muted-foreground max-w-xl mx-auto">
                Submit your best track to compete in SoundWars. Only one submission per artist.
              </p>
            </div>

            {/* Submission Form */}
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* File Upload */}
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                className={`glass rounded-2xl p-8 border-2 border-dashed transition-all ${
                  isDragging
                    ? "border-primary bg-primary/10"
                    : file
                    ? "border-green-500/50 bg-green-500/5"
                    : "border-border hover:border-primary/50"
                }`}
              >
                <input
                  type="file"
                  accept="audio/mpeg"
                  onChange={handleFileChange}
                  className="hidden"
                  id="audio-upload"
                />
                
                <label
                  htmlFor="audio-upload"
                  className="flex flex-col items-center cursor-pointer"
                >
                  {file ? (
                    <>
                      <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mb-4">
                        <Check className="w-8 h-8 text-green-500" />
                      </div>
                      <h3 className="font-semibold text-lg mb-1">{file.name}</h3>
                      <p className="text-sm text-muted-foreground">
                        {(file.size / (1024 * 1024)).toFixed(2)} MB
                      </p>
                      <p className="text-sm text-primary mt-2">Click to change file</p>
                    </>
                  ) : (
                    <>
                      <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center mb-4">
                        <FileAudio className="w-8 h-8 text-primary" />
                      </div>
                      <h3 className="font-semibold text-lg mb-1">
                        Drop your MP3 file here
                      </h3>
                      <p className="text-sm text-muted-foreground mb-4">
                        or click to browse from your device
                      </p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <AlertCircle className="w-4 h-4" />
                        Max file size: 20MB • MP3 format only
                      </div>
                    </>
                  )}
                </label>
              </div>

              {/* Song Details */}
              <div className="glass rounded-2xl p-6 space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="title">Song Title</Label>
                  <div className="relative">
                    <Music className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      id="title"
                      placeholder="Enter your song title"
                      className="pl-10"
                      value={formData.title}
                      onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="description">Song Description</Label>
                  <Textarea
                    id="description"
                    placeholder="Tell us about your song... (optional)"
                    className="min-h-[100px] resize-none"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  />
                </div>
              </div>

              {/* Guidelines */}
              <div className="glass rounded-2xl p-6">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-primary" />
                  Submission Guidelines
                </h3>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                    You can only submit one song per competition
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                    The song must be your original work
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                    File must be in MP3 format, max 20MB
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                    Submissions close when registration period ends
                  </li>
                </ul>
              </div>

              <Button
                type="submit"
                variant="hero"
                size="xl"
                className="w-full"
                disabled={!file || !formData.title}
              >
                <Upload className="w-5 h-5" />
                Submit Track
              </Button>
            </form>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default Submit;
