You are an expert instructor designing an analytic grading rubric for an automatic short-answer grading (ASAG) system.

Task:
Given the question below, generate a grading rubric suitable for partial credit assignment.

Requirements:
1. Decompose the expected answer into BETWEEN 2 AND 5 independent scoring dimensions.
2. Each dimension must correspond to a distinct conceptual or explanatory component that can be present or absent in a student answer.
3. Dimensions must be mutually non-overlapping and collectively sufficient to define a full-credit answer.
4. Assign an integer point value to each dimension. The total must equal 10 points.
5. For each dimension:
   - Provide a concise title.
   - Provide a one-sentence description of what earns full credit for that dimension.
6. Do NOT include example student answers.
7. Do NOT include grading advice, pedagogy, or meta-commentary.
8. Use clear, instructor-style language appropriate for university-level assessment.

Output format (strictly follow):

Rubric:
1. <Dimension title> (<points> points): <full-credit description>
2. ...
Total: 10 points

Question:
<<<
{QUESTION_TEXT}
>>>

