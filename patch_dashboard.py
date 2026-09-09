import re

with open("frontend/src/app/dashboard/page.tsx", "r") as f:
    content = f.read()

# Add History Query
history_query = """
  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['history'],
    queryFn: async () => {
      const res = await api.get('/api/v1/sessions/user/history');
      return res.data.history as any[];
    }
  });
"""

content = content.replace("  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);", history_query + "\n  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);")

# Add History Section
history_section = """
            {/* History Section */}
            <section className="space-y-4 mt-16 pt-8 border-t border-border/40">
              <h2 className="text-sm font-semibold tracking-widest text-muted-foreground uppercase flex items-center">
                <span className="w-6 h-px bg-border mr-4"></span> Recent Interviews
              </h2>
              {historyLoading ? (
                 <div className="flex items-center space-x-3 text-muted-foreground py-4">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Loading history...</span>
                  </div>
              ) : historyData && historyData.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {historyData.map((session, i) => (
                    <div key={session.id} className="p-5 rounded-2xl bg-surface border border-border/40 space-y-2">
                       <div className="flex justify-between items-start">
                         <h3 className="font-semibold text-primary">{session.mode} Interview</h3>
                         <span className="text-xs text-muted-foreground">{new Date(session.created_at).toLocaleDateString()}</span>
                       </div>
                       <p className="text-sm text-muted-foreground">Session ID: {session.id.split('-')[0]}</p>
                       <div className="flex gap-2 mt-2">
                          <span className="px-2 py-1 bg-success/10 text-success text-xs font-medium rounded-full">Completed</span>
                       </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-6 text-center text-muted-foreground bg-surface/30 rounded-2xl border border-dashed border-border/50">
                   No completed interviews yet. Join a queue to get started!
                </div>
              )}
            </section>
"""

content = content.replace("          </div>\n        )}\n      </div>\n    </AppLayout>", history_section + "\n          </div>\n        )}\n      </div>\n    </AppLayout>")

with open("frontend/src/app/dashboard/page.tsx", "w") as f:
    f.write(content)
