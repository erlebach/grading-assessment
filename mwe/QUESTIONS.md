- Why is batch mode async given that there is only a single call? 
  One reason: if there are 8 students, you could divide them in two groups of 4 submitted via async
- why run main_async in async mode? It is only executed once and nothing can run at the same time. 
- How does async work? Does it require multi-threading?
