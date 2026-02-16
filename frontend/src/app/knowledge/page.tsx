"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ingestDocument, queryKnowledge } from "@/lib/api";
import type { KnowledgeChunk } from "@/lib/types";

export default function KnowledgePage() {
  // Upload state
  const [uploadContent, setUploadContent] = useState("");
  const [uploadSource, setUploadSource] = useState("");
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [searchResults, setSearchResults] = useState<KnowledgeChunk[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);

  async function handleUpload() {
    if (!uploadContent.trim() || uploadLoading) return;
    setUploadLoading(true);
    setUploadResult(null);

    try {
      const res = await ingestDocument({
        content: uploadContent.trim(),
        source: uploadSource.trim() || undefined,
      });
      setUploadResult(res.message);
      setUploadContent("");
      setUploadSource("");
    } catch (err) {
      setUploadResult(
        `Error: ${err instanceof Error ? err.message : "Unknown error"}`
      );
    } finally {
      setUploadLoading(false);
    }
  }

  async function handleSearch() {
    if (!searchQuery.trim() || searchLoading) return;
    setSearchLoading(true);

    try {
      const res = await queryKnowledge({
        query: searchQuery.trim(),
        top_k: topK,
      });
      setSearchResults(res.results);
    } catch {
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold">Knowledge</h2>

      {/* Upload Section */}
      <Card data-testid="upload-section">
        <CardHeader>
          <CardTitle>Upload Document</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Textarea
            placeholder="Paste document content..."
            value={uploadContent}
            onChange={(e) => setUploadContent(e.target.value)}
            data-testid="upload-content"
          />
          <Input
            placeholder="Source (optional)"
            value={uploadSource}
            onChange={(e) => setUploadSource(e.target.value)}
            data-testid="upload-source"
          />
          <Button
            onClick={handleUpload}
            disabled={uploadLoading || !uploadContent.trim()}
            data-testid="upload-button"
          >
            Upload
          </Button>
          {uploadResult && (
            <p className="text-sm text-muted-foreground" data-testid="upload-result">
              {uploadResult}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Search Section */}
      <Card data-testid="search-section">
        <CardHeader>
          <CardTitle>Search Knowledge</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input
            placeholder="Search query..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSearch();
            }}
            data-testid="search-query"
          />
          <Input
            type="number"
            placeholder="Top K results"
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value) || 5)}
            min={1}
            max={20}
            data-testid="search-top-k"
          />
          <Button
            onClick={handleSearch}
            disabled={searchLoading || !searchQuery.trim()}
            data-testid="search-button"
          >
            Search
          </Button>

          <div className="space-y-2" data-testid="search-results">
            {searchResults.map((chunk, i) => (
              <Card key={i} data-testid="result-card">
                <CardContent className="pt-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">{chunk.source}</span>
                    <Badge variant="outline">
                      {(chunk.similarity * 100).toFixed(1)}%
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{chunk.content}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
