1. In the context of a data table, precisely distinguish an “object” from an “attribute,” and give two alternative names for each (as used in data mining practice). 
   Good answer: An object is a row-level entity in the dataset (a “data object,” often also called an instance, example, or sample). An attribute is a column-level variable describing objects (often also called a feature, variable, or dimension). In the data-matrix view, objects are points in an n-dimensional space and each dimension corresponds to an attribute. 
   Less good answer: An object is basically a row and an attribute is basically a column; attributes define the dimensions and each row is a point in that space. 
   Wrong answer (still “about” the slides): An object is a column (attribute) and an attribute is a row (object); the matrix is n-by-m with n objects as columns and m attributes as rows. 

2. The slides emphasize that an attribute’s properties—not the apparent data type of its stored values—determine valid analyses and transformations. Explain this principle using the zip code example, and state one analysis that would be inappropriate if you mistakenly treated zip codes as numeric. 
   Good answer: Zip code values may be stored as integers, but the attribute “zip code” is nominal: it supports distinctness (equality/inequality) but not meaningful order, differences, or ratios. Therefore, treating zip codes as numeric and computing means/standard deviations or Pearson correlation is inappropriate; you would instead use nominal-appropriate summaries and tests (e.g., mode, contingency analysis, chi-square). 
   Less good answer: Even if zip codes look like numbers, they’re categorical labels, so arithmetic like averaging them is not meaningful; you should analyze them like categories. 
   Wrong answer: Zip codes are integers, so differences between them are meaningful; it is reasonable to compute the mean zip code for a county and interpret it as a “central location.” 

3. Nominal, ordinal, interval, and ratio attributes differ by which operations are “meaningful.” For each type, state which of the following are meaningful: distinctness (=, ≠), order (<, >), differences (+, −), ratios (×, ÷). 
   Good answer: Nominal supports distinctness only. Ordinal supports distinctness and order. Interval supports distinctness, order, and meaningful differences. Ratio supports all four: distinctness, order, meaningful differences, and meaningful ratios. 
   Less good answer: Nominal is just equality/inequality; ordinal adds ordering; interval adds subtraction; ratio adds division/multiplication meaningfully. 
   Wrong answer: Ordinal and interval both allow meaningful ratios, because both have ordering and numeric values. 

4. Why is it not physically meaningful to say that 10° is “twice as warm” as 5° on the Celsius or Fahrenheit scales, but it is meaningful on the Kelvin scale? State the key role played by the zero point. 
   Good answer: Celsius and Fahrenheit are interval scales: differences are meaningful, but the zero point is not an absence of temperature, so ratios like 10/5 are arbitrary under a shift of origin. Kelvin is ratio: zero Kelvin corresponds to absence of temperature, making ratios physically meaningful. 
   Less good answer: Kelvin has a “true zero,” so “twice as warm” can be meaningful there, while Celsius/Fahrenheit have shifted zero points so ratio statements break. 
   Wrong answer: Celsius and Fahrenheit are ratio scales because they have a zero value; therefore, saying 10°C is twice 5°C is meaningful. 

5. A measurement scale can preserve only ordering or can preserve ordering plus additivity. Explain what “preserving only ordering” means, and describe one practical consequence for computations you should (or should not) perform. 
   Good answer: “Preserving only ordering” corresponds to ordinal attributes: any order-preserving (monotonic) recoding keeps the meaning, but differences/ratios between codes are not meaningful. Practically, you should use medians, percentiles, or rank-based methods rather than means/standard deviations or Pearson correlation, because the numeric gaps may be arbitrary.
   Less good answer: For ordinal data you can sort and compare who is higher/lower, but you should not treat the spacing between levels as real; use ranks or medians instead of averages. 
   Wrong answer: Preserving only ordering means you can add and subtract ordinal values reliably (e.g., “best − good = 2”), so using means and standard deviations is appropriate. 

6. The Stevens transformation rules differ by attribute type. For each type (nominal, ordinal, interval, ratio), describe the class of allowable transformations and why they preserve meaning. 
   Good answer: Nominal: any permutation (relabeling) preserves meaning because only distinctness matters. Ordinal: any monotonic (order-preserving) function preserves meaning because only rank order matters. Interval: new = a·old + b preserves meaning because differences are preserved up to a scale factor (changing unit and origin, like Celsius vs Fahrenheit). Ratio: new = a·old (with positive a) preserves meaning because ratios are preserved under unit changes (e.g., meters vs feet). 
   Less good answer: Nominal lets you rename categories; ordinal lets you remap values as long as order stays; interval allows scaling and shifting; ratio allows scaling only, reflecting a meaningful zero. 
   Wrong answer: Interval data allow any monotonic transformation (like ordinal), while ordinal data require linear transformations (a·x+b) to preserve the size of differences. 

7. Define discrete vs continuous attributes as presented in the slides. Then explain why continuous attributes are still represented with a finite number of digits in practice, and what this implies about measurement/precision. 
   Good answer: Discrete attributes take a finite or countably infinite set of values (often integers; binary is a special case). Continuous attributes have real-valued measurements (e.g., height/weight/temperature), but in practice they can only be measured and stored with finite digits, typically as floating point. This implies quantization/measurement error: the “true” value is approximated and precision is bounded by instrument and representation. 
   Less good answer: Discrete is countable; continuous is real-valued, but we store continuous values approximately (finite digits), so we never have perfect precision. 
   Wrong answer: Continuous attributes are stored exactly as real numbers in computers, so there is no measurement/representation limitation; only discrete attributes suffer from finite representation. 

8. What is an asymmetric attribute? Provide one example from document or transaction data, and explain why “both zeros” (absence/absence) should not be treated as strong evidence of similarity. 
   Good answer: An asymmetric attribute is one where only presence (a non-zero value) is considered informative; absence is not. Examples include words present in documents or items present in customer transactions. Two zeros (“neither document contains the word,” “neither basket contains the item”) are common and uninformative, so counting them as matching would inflate similarity for sparse data.
   Less good answer: In text/market-basket data, presence matters; shared absences are not very meaningful because there are so many possible words/items that are absent everywhere. 
   Wrong answer: Asymmetric means that the “0” value is the important one; therefore, two zeros should be treated as a strong match and dominate the similarity score in transaction and document data. 

9. Compare record (data matrix), document data (term vectors), and transaction data. For each, specify what an “object” corresponds to and what the “attributes” correspond to.
   Good answer: Record/data matrix: each object is a row (entity/instance), each attribute is a column (variable/dimension). Document data: each object is a document; attributes are terms; values are term counts (or sometimes presence/absence). Transaction data: each object is a transaction; attributes correspond to items (often represented as binary presence/absence per item).
   Less good answer: Record data is the usual row/column matrix; document data makes documents into vectors of word counts; transaction data makes baskets into sets of items (or a binary item matrix).
   Wrong answer: In document data, each term is an object and each document is an attribute; in transaction data, each item is an object and each transaction is an attribute.

10. The slides list several data quality problems (noise, outliers, missing values, duplicates, wrong/fake data). Pick two and describe (i) one way to detect the problem and (ii) one principled way to address it, including a brief note on when “cleaning” could backfire.
    Good answer:
    • Noise (attribute noise): Detect via signal diagnostics (e.g., unexpected high-frequency variation or distortion relative to an expected pattern); address via smoothing/denoising or improved measurement processes, recognizing the slide’s point that noise can distort magnitude/shape. 
    • Missing values: Detect via missingness summaries and patterns (by attribute/object); address by eliminating objects/variables, estimating missing values (e.g., time-series interpolation), or ignoring missing values during analysis depending on context. Cleaning can backfire if, for example, you eliminate too much data or impute in a way that biases downstream models. 
    Less good answer:
    • Outliers: Detect by spotting points far from the bulk of the data; handle by removing them if they are noise, or keeping them if they are the phenomenon of interest (e.g., fraud/intrusion). 
    • Duplicates: Detect by looking for identical or near-identical rows (common when merging sources); handle by data cleaning/deduplication, but be cautious because “almost duplicates” can be ambiguous (e.g., how many matching attributes is “enough” to merge/remove). 
    Wrong answer:
    • Outliers: Detect by checking whether noise is present; if there is no noise, there cannot be outliers. Address by always deleting outliers because they are never useful. 

