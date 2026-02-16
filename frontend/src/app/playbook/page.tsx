"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { fetchPlaybook, resetPlaybook } from "@/lib/api";
import type { PlaybookEntry, PlaybookResponse } from "@/lib/types";

export default function PlaybookPage() {
  const [data, setData] = useState<PlaybookResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    loadPlaybook();
  }, []);

  function loadPlaybook() {
    setLoading(true);
    fetchPlaybook()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }

  async function handleReset() {
    setResetting(true);
    try {
      await resetPlaybook();
      setResetDialogOpen(false);
      loadPlaybook();
    } catch {
      // keep dialog open on error
    } finally {
      setResetting(false);
    }
  }

  // Group entries by section
  const grouped = (data?.entries ?? []).reduce<Record<string, PlaybookEntry[]>>(
    (acc, entry) => {
      const section = entry.section || "Uncategorized";
      if (!acc[section]) acc[section] = [];
      acc[section].push(entry);
      return acc;
    },
    {}
  );

  if (loading) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-bold">Playbook</h2>
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Playbook</h2>
        <Dialog open={resetDialogOpen} onOpenChange={setResetDialogOpen}>
          <DialogTrigger asChild>
            <Button variant="destructive" data-testid="reset-button">
              Reset Playbook
            </Button>
          </DialogTrigger>
          <DialogContent data-testid="reset-dialog">
            <DialogHeader>
              <DialogTitle>Reset Playbook</DialogTitle>
              <DialogDescription>
                This will permanently reset all playbook entries and feedback
                data. This action cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setResetDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleReset}
                disabled={resetting}
                data-testid="confirm-reset"
              >
                {resetting ? "Resetting..." : "Confirm Reset"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats Banner */}
      <Card data-testid="stats-banner">
        <CardContent className="flex flex-wrap gap-6 pt-4">
          {data?.stats &&
            Object.entries(data.stats).map(([key, value]) => (
              <div key={key} className="text-center">
                <p className="text-2xl font-bold">{String(value)}</p>
                <p className="text-sm text-muted-foreground">{key}</p>
              </div>
            ))}
          {(!data?.stats || Object.keys(data.stats).length === 0) && (
            <p className="text-muted-foreground">No stats available</p>
          )}
        </CardContent>
      </Card>

      {/* Grouped Entries */}
      <div className="space-y-6" data-testid="playbook-entries">
        {Object.entries(grouped).map(([section, entries]) => (
          <div key={section}>
            <h3 className="text-lg font-semibold mb-3">{section}</h3>
            <div className="space-y-2">
              {entries.map((entry) => (
                <Card key={entry.id} data-testid="playbook-entry">
                  <CardContent className="flex items-start justify-between gap-4 pt-4">
                    <div className="flex-1">
                      <p className="text-sm">{entry.content}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {entry.entry_id}
                      </p>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <Badge
                        variant="default"
                        data-testid="helpful-badge"
                      >
                        +{entry.helpful_count}
                      </Badge>
                      <Badge
                        variant="destructive"
                        data-testid="harmful-badge"
                      >
                        -{entry.harmful_count}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ))}
        {Object.keys(grouped).length === 0 && (
          <p className="text-muted-foreground">No playbook entries yet.</p>
        )}
      </div>
    </div>
  );
}
