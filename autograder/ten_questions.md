1. In the context of a data table, precisely distinguish an “object” from an “attribute,” and give two alternative names for each (as used in data mining practice). 

2. The slides emphasize that an attribute’s properties—not the apparent data type of its stored values—determine valid analyses and transformations. Explain this principle using the zip code example, and state one analysis that would be inappropriate if you mistakenly treated zip codes as numeric. 

3. Nominal, ordinal, interval, and ratio attributes differ by which operations are “meaningful.” For each type, list which of the following are meaningful: distinctness (=, ≠), order (<, >), differences (+, −), ratios (×, ÷). 

4. Why is it not physically meaningful to say that 10° is “twice as warm” as 5° on the Celsius or Fahrenheit scales, but it is meaningful on the Kelvin scale? State the key role played by the zero point. 

5. A measurement scale can preserve only ordering or can preserve ordering plus additivity. Explain what “preserving only ordering” means, and describe one practical consequence for computations you should (or should not) perform. 

6. The Stevens transformation rules differ by attribute type. For each type (nominal, ordinal, interval, ratio), describe the class of allowable transformations (e.g., “any permutation,” “monotone function,” “a·x+b,” etc.) and briefly justify why those transformations preserve meaning. 

7. Define discrete vs continuous attributes as presented in the slides. Then explain why continuous attributes are still represented with a finite number of digits in practice, and what this implies about measurement/precision. 

8. What is an asymmetric attribute? Provide one example from text/document analysis or market-basket (transaction) data, and explain why “both zeros” (absence/absence) should not be treated as strong evidence of similarity. 

9. Compare three dataset types discussed: record (data matrix), document data (term vectors), and transaction data. For each, specify what an “object” corresponds to and what the “attributes” correspond to. 

10. The slides list several data quality problems (noise, outliers, missing values, duplicates, wrong/fake data). Pick two of these and describe (i) one way to detect the problem and (ii) one principled way to address it, including a brief note on when “cleaning” could backfire. 

