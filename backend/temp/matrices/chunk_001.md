<figure>

<!-- PageHeader="Chapter 3" -->
<!-- PageHeader="12079CH03" -->

</figure>


# MATRICES


## The essence of Mathematics lies in its freedom. - CANTOR


### 3.1 Introduction

The knowledge of matrices is necessary in various branches of mathematics. Matrices
are one of the most powerful tools in mathematics. This mathematical tool simplifies
our work to a great extent when compared with other straight forward methods. The
evolution of concept of matrices is the result of an attempt to obtain compact and
simple methods of solving system of linear equations. Matrices are not only used as a
representation of the coefficients in system of linear equations, but utility of matrices
far exceeds that use. Matrix notation and operations are used in electronic spreadsheet
programs for personal computer, which in turn is used in different areas of business
and science like budgeting, sales projection, cost estimation, analysing the results of an
experiment etc. Also, many physical operations such as magnification, rotation and
reflection through a plane can be represented mathematically by matrices. Matrices
are also used in cryptography. This mathematical tool is not only used in certain branches
of sciences, but also in genetics, economics, sociology, modern psychology and industrial
management.

a

In this chapter, we shall find it interesting to become acquainted with the
fundamentals of matrix and matrix algebra.


### 3.2 Matrix

Suppose we wish to express the information that Radha has 15 notebooks. We may
express it as [15] with the understanding that the number inside [ ] is the number of
notebooks that Radha has. Now, if we have to express that Radha has 15 notebooks
and 6 pens. We may express it as [15 6] with the understanding that first number
inside [ ] is the number of notebooks while the other one is the number of pens possessed
by Radha. Let us now suppose that we wish to express the information of possession

<!-- PageFooter="Reprint 2024-25" -->
<!-- PageBreak -->

<!-- PageNumber="35" -->
<!-- PageHeader="MATRICES" -->

of notebooks and pens by Radha and her two friends Fauzia and Simran which
is as follows:


<table>
<tr>
<td>Radha</td>
<td>has</td>
<td>15</td>
<td>notebooks</td>
<td>and</td>
<td>6 pens,</td>
</tr>
<tr>
<td>Fauzia</td>
<td>has</td>
<td>10</td>
<td>notebooks</td>
<td>and</td>
<td>2 pens,</td>
</tr>
<tr>
<td>Simran</td>
<td>has</td>
<td>13</td>
<td>notebooks</td>
<td>and</td>
<td>5 pens.</td>
</tr>
</table>


Now this could be arranged in the tabular form as follows:


<table>
<tr>
<th></th>
<th>Notebooks</th>
<th>Pens</th>
</tr>
<tr>
<td>Radha</td>
<td>15</td>
<td>6</td>
</tr>
<tr>
<td>Fauzia</td>
<td>10</td>
<td>2</td>
</tr>
<tr>
<td>Simran</td>
<td>13</td>
<td>5</td>
</tr>
</table>


and this can be expressed as


<figure>

15

6
2
ICERS

<- Third row
15
6
15
6
not be ph wished

« First row

10

<- Second row

13

5
1
Second
Column

1

First
Column

or

Radha

Fauzia

Simran

Notebooks

10

13

Pens

2

5

which can be expressed as:

10

13

< First row

2

5

< Second row

1

1

First
Column

Second
Column

↑
Third
Column

</figure>


In the first arrangement the entries in the first column represent the number of
note books possessed by Radha, Fauzia and Simran, respectively and the entries in the
second column represent the number of pens possessed by Radha, Fauzia and Simran,

<!-- PageFooter="Reprint 2024-25" -->
