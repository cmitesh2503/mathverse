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


================================================================================

<!-- PageNumber="36" -->
<!-- PageHeader="MATHEMATICS" -->

respectively. Similarly, in the second arrangement, the entries in the first row represent
the number of notebooks possessed by Radha, Fauzia and Simran, respectively. The
entries in the second row represent the number of pens possessed by Radha, Fauzia
and Simran, respectively. An arrangement or display of the above kind is called a
matrix. Formally, we define matrix as:

Definition 1 A matrix is an ordered rectangular array of numbers or functions. The
numbers or functions are called the elements or the entries of the matrix.

We denote matrices by capital letters. The following are some examples of matrices:

A= 0 5 ,B=
3
-2 5
6
, B- 3,5 -1 2, C
V3
☒

2+i 3 1
5

a

2
7
C=

x3
5
1+x
cos x sin x+ 2 tan x
3

In the above examples, the horizontal lines of elements are said to constitute, rows
of the matrix and the vertical lines of elements are said to constitute, columns of the
matrix. Thus A has 3 rows and 2 columns, B has 3 rows and 3 columns while C has 2
rows and 3 columns.


# 3.2.1 Order of a matrix

A matrix having m rows and n columns is called a matrix of order m × n or simply m × n
matrix (read as an m by n matrix). So referring to the above examples of matrices, we
have A as 3 × 2 matrix, B as 3 × 3 matrix and C as 2 × 3 matrix. We observe that A has
3 × 2 = 6 elements, B and C have 9 and 6 elements, respectively.

In general, an m × n matrix has the following rectangular array:

a11
a
il
Esta

a12 @13 ... alj ... aIn

@23 ... a2j ... @2n

a22
am1 am2 am3 ". amj ... amn
a21

m xn

or A =[a ] > , 1≤i ≤m, 1≤j≤n i,jeN

Thus the ith row consists of the elements a 1, a2, a 3, ... , a , while the jth column
consists of the elements alp a2p a3j .... , amj?

In general a , is an element lying in the ith row and jth column. We can also call
it as the (i, j)th element of A. The number of elements in an m x n matrix will be
ij?
equal to mn.

<!-- PageFooter="Reprint 2024-25" -->
<!-- PageBreak -->

<!-- PageNumber="37" -->
<!-- PageHeader="MATRICES" -->


## Note In this chapter

1\. We shall follow the notation, namely A = [a ] to indicate that A is a matrix
of order m x n.
ij-m xn

2\. We shall consider only those matrices whose elements are real numbers or
functions taking real values.

We can also represent any point (x, y) in a plane by a matrix (column or row) as

x

(or [x, y]). For example point P(0, 1) as a matrix representation may be given as

y

0

or [0 1].

Observe that in this way we can also express the vertices of a closed rectilinear
figure in the form of a matrix. For example, consider a quadrilateral ABCD with vertices
A (1, 0), B (3,2), C (1,3), D (-1,2).

Now, quadrilateral ABCD in the matrix form, can be represented as

X =
ABCD
3

1 3 1 -1
0 2

2
2× 4
or

Y =

A
B
C

-1
1
1

0

3

2

3

D

2

4×2

Thus, matrices can be used as representation of vertices of geometrical figures in
a plane.

Now, let us consider some examples.

Example 1 Consider the following information regarding the number of men and women
workers in three factories I, II and III


<table>
<tr>
<th></th>
<th>Men workers</th>
<th>TE Women workers</th>
</tr>
<tr>
<td>I</td>
<td>30</td>
<td>25</td>
</tr>
<tr>
<td>II</td>
<td>25</td>
<td>31</td>
</tr>
<tr>
<td>III</td>
<td>27</td>
<td>26</td>
</tr>
</table>


Represent the above information in the form of a 3 x 2 matrix. What does the entry
in the third row and second column represent?

<!-- PageFooter="Reprint 2024-25" -->


================================================================================

<!-- PageNumber="38" -->
<!-- PageHeader="MATHEMATICS" -->

Solution The information is represented in the form of a 3 x 2 matrix as follows:

30 25
A= 25 31
27
26

The entry in the third row and second column represents the number of women
workers in factory III.

Example 2 If a matrix has 8 elements, what are the possible orders it can have?

Solution We know that if a matrix is of order m x n, it has mn elements. Thus, to find
all possible orders of a matrix with 8 elements, we will find all ordered pairs of natural
numbers, whose product is 8.

Thus, all possible ordered pairs are (1, 8), (8, 1), (4, 2), (2, 4)
Hence, possible orders are 1 × 8, 8 ×1, 4 × 2, 2 ×4

Example 3 Construct a 3 × 2 matrix whose elements are given by aj = ~ | i - 3 j |.

Solution In general a 3 x 2 matrix is given by A = @21 a22 .

1
2
a11 a12
a31 @32

Now
@j=\i-3jl, i=1, 2, 3 and j=1, 2.

Therefore
a1 =~ |1-3x1|=1

1

@12 =~ |1-3x2|=>

2

5
2

@21 =~ |2-3x1| =-

@31 == |3-3x1|=0
1
2
1
2

1
1
2
2
@22 =~ |2-3x2|=2

a32 =~ /3-3x2|=>

3
2

Hence the required matrix is given by A =

1
1
2

1
2
5
3

0

2
2
2

<!-- PageFooter="Reprint 2024-25" -->

1
2
1
2

<!-- PageBreak -->

<!-- PageNumber="39" -->
<!-- PageHeader="MATRICES" -->


# 3.3 Types of Matrices

In this section, we shall discuss different types of matrices.


## (i) Column matrix

A matrix is said to be a column matrix if it has only one column.

0

V3

For example, A = - 1 |is a column matrix of order 4 x 1.

1/2

In general, A = [a ]
m × 1
is a column matrix of order m × 1.

(ii)
Row matrix

A matrix is said to be a row matrix if it has only one row.

For example, B = -- 5 2 3 is a row matrix.
2

1×4

In general, B = [b]]
1 xn
is a row matrix of order 1 x n.

(iii) Square matrix

A matrix in which the number of rows are equal to the number of columns, is
said to be a square matrix. Thus an m × n matrix is said to be a square matrix if
m = n and is known as a square matrix of order 'n'.

3
2

-1
3

07

For example A = ~ 3V2 1 |is a square matrix of order 3.
4
3

-1

In general, A = [a ]
m xm
is a square matrix of order m.


<figure>

Note If A = [a ] is a square matrix of order n, then elements (entries) a 11, a22. ... , am

1 -3 1
are said to constitute the diagonal, of the matrix A. Thus, if A = 2 4 -1.
3 5 6

Then the elements of the diagonal of A are 1, 4, 6.

</figure>


<!-- PageFooter="Reprint 2024-25" -->


================================================================================

<!-- PageNumber="40" -->
<!-- PageHeader="MATHEMATICS" -->


# (iv) Diagonal matrix

A square matrix B = [b]]
m xm
is said to be a diagonal matrix if all its non
diagonal elements are zero, that is a matrix B = [b]] mx„ is said to be a diagonal
matrix if b = 0, when i + j.

-1 0
›
-1.1 0 0
0

For example, A = [4], B =
\- 0 2 C= 0 2 0 , are diagonal

0
3
, matrices
of order 1, 2, 3, respectively.


# (v) Scalar matrix

A diagonal matrix is said to be a scalar matrix if its diagonal elements are equal,
that is, a square matrix B = [b ]
ij-nxn
is said to be a scalar matrix if

b = 0, when i + j
įj
b = k, when i = j, for some constant k.
įj

For example

-1

0
-1

,
C=

0

0

are scalar matrices of order 1, 2 and 3, respectively.


# (vi) Identity matrix

A square matrix in which elements in the diagonal are all 1 and rest are all zero
is called an identity matrix. In other words, the square matrix A = [a ]
is an

ij-nxn
identity matrix, if dj =

[1 if i=j
0 if iøj

We denote the identity matrix of order n by I. When order is clear from the
context, we simply write it as I.

100

For example [1],
1
0
0
17001

,
010
are identity matrices of order 1, 2 and 3,
respectively.

Observe that a scalar matrix is an identity matrix when k = 1. But every identity
matrix is clearly a scalar matrix.

<!-- PageFooter="Reprint 2024-25" -->

0
0
0
0
0
3
Esta

<!-- PageBreak -->

<!-- PageNumber="41" -->
<!-- PageHeader="MATRICES" -->


# (vii) Zero matrix

A matrix is said to be zero matrix or null matrix if all its elements are zero.

0 07 000

For example, [0],
0 0, 0 0 0 7
[0, 0] are all zero matrices. We denote
zero matrix by O. Its order will be clear from the context.


## 3.3.1 Equality of matrices

Definition 2 Two matrices A = [a ] and B = [b]] are said to be equal if

(i) they are of the same order

(ii) each element of A is equal to the corresponding element of B, that is a = b for
ij
all i and j.

For example,
e, 0 1]and 0 1
2

2

3
are equal matrices but
3
3
and

0
2
1

ij
2
0
3

1
are
not equal matrices. Symbolically, if two matrices A and B are equal, we write A = B.

If z a = 2 V6 , then x =- 1.5, y = 0, 2=2, a = V6, b = 3, c=2
b
x

y
C
-1.5
3
.5 0
2
☒
b-3 -21
x+3 z+4 2y-7
Example 4 If |-6 a-1 0 =- 6 -3 2c+2

6 3y-2
0
Find the values of a, b, c, x, y and z.

0
☒
0
2b+4 -21

Solution As the given matrices are equal, therefore, their corresponding elements
must be equal. Comparing the corresponding elements, we get

x + 3 =0,
a - 1 =- 3,
z + 4 = 6,
0=2c +2
2y -7=3y-2
b - 3 = 2b+4,

Simplifying, we get

Example 5 Find the values of a, b, c, and d from the following equation:

a =- 2, b =- 7,c =- 1,x =- 3, y =- 5, z=2
2a+b a-2b
5c-d 4c+3d 11 24
4
-3

<!-- PageFooter="Reprint 2024-25" -->


================================================================================

<!-- PageNumber="42" -->
<!-- PageHeader="MATHEMATICS" -->

Solution By equality of two matrices, equating the corresponding elements, we get

2a + b = 4
a - 2b =- 3

5c - d = 11
4c + 3d = 24

Solving these equations, we get

a = 1, b =2,c=3and d=4


# EXERCISE 3.1

2 5 19 -77

1\. In the matrix A =
35

72 2 12 , write
-2
5
☒

V3 1 -5 17

(i) The order of the matrix,
(ii) The number of elements,

(iii) Write the elements a13, a21, a33, @24, @23-

2\. If a matrix has 24 elements, what are the possible orders it can have? What, if it
has 13 elements?

3\. If a matrix has 18 elements, what are the possible orders it can have? What, if it
has 5 elements?

4\. Construct a 2 × 2 matrix, A = [a ], whose elements are given by:

(i) aj = 2
(i + j)2

(ii) aj =-
i
j

(iii) a = (i +2j)2
=2

5\. Construct a 3 × 4 matrix, whose elements are given by:

(i) @jj == |-3i+j|(ii) aj=2i-j
1
2

6\. Find the values of x, y and z from the following equations:

4 3
(1) x 5 1 5 (1)
Z
\=
y

i) X+ y 2 _ 6 2
5+z xy -5 8 (iii)
x+y+z
9

y +z
+2 = 5
7

7\. Find the value of a, b, c and d from the equation:

a-b 2a+c -1 5
2a-b 3c+d 0 13

<!-- PageFooter="Reprint 2024-25" -->
<!-- PageBreak -->

<!-- PageNumber="43" -->
<!-- PageHeader="MATRICES" -->

8\. A = [a ]
ij-m xnl
is a square matrix, if
(A) m<n
(B) m>n
(C) m =n
(D) None of these

9\. Which of the given values of x and y make the following pair of matrices equal

[

3x+7 5 ] 0 y-2
y +1 2-3x , 8 4
(A) x =- , y=7
-1

(B) Not possible to find

-2

(C) y=7, x =_

3

(D) x= 3, y=3

10\. The number of all possible matrices of order 3 × 3 with each entry 0 or 1 is:
(A) 27

(B) 18
(C) 81
(D) 512


## 3.4 Operations on Matrices

In this section, we shall introduce certain operations on matrices, namely, addition of
matrices, multiplication of a matrix by a scalar, difference and multiplication of matrices.


### 3.4.1 Addition of matrices

Suppose Fatima has two factories at places A and B. Each factory produces sport
shoes for boys and girls in three different price categories labelled 1, 2 and 3. The
quantities produced by each factory are represented as matrices given below:

La
Factory at A
Factory at B
Boys
Girls
Boys
1
80
60
1
90
2
75
65
2
3
90
VaE
85


<figure>

Girls

50

70

55

3

75

75

</figure>


Suppose Fatima wants to know the total production of sport shoes in each price
category. Then the total production

In category 1 : for boys (80 + 90), for girls (60 +50)
In category 2 : for boys (75 + 70), for girls (65 + 55)
In category 3 : for boys (90 + 75), for girls (85 + 75)


<table>
<tr>
<th></th>
<th>80+90</th>
<th>60+50</th>
</tr>
<tr>
<td rowspan="2">This can be represented in the matrix form as</td>
<td>75+70</td>
<td>65+55</td>
</tr>
<tr>
<td>90+75</td>
<td>85+75</td>
</tr>
</table>


<!-- PageFooter="Reprint 2024-25" -->


================================================================================

<!-- PageNumber="44" -->
<!-- PageHeader="MATHEMATICS" -->

This new matrix is the sum of the above two matrices. We observe that the sum of
two matrices is a matrix obtained by adding the corresponding elements of the given
matrices. Furthermore, the two matrices have to be of the same order.

is a 2 × 3 matrix and B =
@11 @12 @13
b11 b12 b13
b21 b22 b23
3
is another
Thus, if A =

a21 @22 @23

2×3 matrix. Then, we define A + B =

@11+b11 @12 +b12 @13 + b13
@21 +b21 @22 + b22 @23 + b23
\-

In general, if A = [a ] and B = [b ] are two matrices of the same order, say m x n.
Then, the sum of the two matrices A and B is defined as a matrix C = [c ]_ __ , where
cj = ay + by for all possible values of i and j.

Example 6 Given A =
V3
2

V5

1
3
-1
0
and B=
2
-2 3 2
1
,

Since A, B are of the same order 2 x 3. Therefore, addition of A and B is defined
and is given by

2+13 1+15 1-1

A+B=
2-2 3+3 0+-
1
2
\=

0
2+13 1+15
6
0

1
find A + B
Varde ale ta KE

1
2


# Note

1\. We emphasise that if A and B are not of the same order, then A + B is not
defined. For example if A =
3
›

2
0

1
3
then A + B is not defined.
,

1

2\. We may observe that addition of matrices is an example of binary operation
on the set of matrices of the same order.


## 3.4.2 Multiplication of a matrix by a scalar

Now suppose that Fatima has doubled the production at a factory A in all categories
(refer to 3.4.1).

<!-- PageFooter="Reprint 2024-25" -->
<!-- PageBreak -->

<!-- PageNumber="45" -->
<!-- PageHeader="MATRICES" -->

Previously quantities (in standard units) produced by factory A were


<table>
<tr>
<th></th>
<th>Boys</th>
<th>Girls</th>
</tr>
<tr>
<td>1</td>
<td>80</td>
<td>60</td>
</tr>
<tr>
<td>2</td>
<td>75</td>
<td>65</td>
</tr>
<tr>
<td>3</td>
<td>90</td>
<td>85</td>
</tr>
</table>


Revised quantities produced by factory A are as given below:


<table>
<tr>
<th></th>
<th></th>
<th>Boys</th>
<th>Girls</th>
</tr>
<tr>
<td>1</td>
<td></td>
<td>2×80</td>
<td>2×60</td>
</tr>
<tr>
<td colspan="3">2 2×75</td>
<td>2×65</td>
</tr>
<tr>
<td colspan="2">3</td>
<td>2×90</td>
<td>2×85</td>
</tr>
</table>


160

This can be represented in the matrix form as

150

130 . We observe that

170

120
180 0 Shed

the new matrix is obtained by multiplying each element of the previous matrix by 2.

In general, we may define multiplication of a matrix by a scalar as follows: if
A = [a ]
ij-mxn
is a matrix and k is a scalar, then kA is another matrix which is obtained
by multiplying each element of A by the scalar k.

In other words, kA = k [a]] mx n = [k (at)]
m x nº
that is, (i, j)th element of kA is ka,
for all possible values of i and j.

For example, if
A= 15 7 -3 ,then

1
☒
3
2 0 5
☒
not"tas , 15
3A = 3
V5 7 -3 = 3 5 21 -9
2 0 5 6 0 15
9
3
4.5
☒
3 1 1.5

Negative of a matrix The negative of a matrix is denoted by -A. We define
-A =(-1) A.

<!-- PageFooter="Reprint 2024-25" -->


================================================================================

<!-- PageNumber="46" -->
<!-- PageHeader="MATHEMATICS" -->

For example, let

A = - 5 x 3
3

1
then - A is given by
,

-A = (-1)A =(-1)

3
-5 x = 5 - x
1
-3
-1
1
-x

Difference of matrices If A = [a ], B = [b ] are two matrices of the same order,
say m x n, then difference A - B is defined as a matrix D = [d ], where d = a¡ - bij
for all value of i and j. In other words, D =A-B=A +(-1) B, that is sum of the matrix
A and the matrix - B.

Example 7 If A =
123
2 3 1
and B =
-1
3 -1 3
0

\>
then find 2A - B.

2

Solution We have

2A -B= 2

2
\=
1
2
2
3

3
1

\-

-1
3 -13]
0

4
3
1
-3
4 62 10 -2
6
+

=
4+1 6+0 2-2 5 60

2
\=
Hp Je lls Publishedim
2-3 4+1 6-3 -1 5 3


# 3.4.3 Properties of matrix addition

The addition of matrices satisfy the following properties:

(i) Commutative Law If A = [a ], B = [b ] are matrices of the same order, say
m × n, then A + B = B +A.

Now
A + B = [a ] + [b]] = [a] + b]]
= [b] + a ] (addition of numbers is commutative)
= ([b]] + [a ]) = B + A

(ii) Associative Law For any three matrices A = [a ], B = [b], C = [c ] of the
same order, say m × n, (A + B) + C = A + (B + C).
Now (A + B) + C = ([a]] + [b]]) + [c]]
=[a] + byj] + [c]] = [(ag + by) + cy]
=[a] + (bij + cu)]

(Why?)
= [a]] + [(b ) + cu)] = [a ] + ([b]] + [c]]) = A + (B + C)

<!-- PageFooter="Reprint 2024-25" -->
<!-- PageBreak -->

<!-- PageNumber="47" -->
<!-- PageHeader="MATRICES" -->

(iii) Existence of additive identity Let A = [a ] be an m x n matrix and
O be an m x n zero matrix, then A + O = O + A = A. In other words, O is the
additive identity for matrix addition.

(iv) The existence of additive inverse Let A = [a ]

ij-m xn
be any matrix, then we
have another matrix as - A = [- a ] , such that A + (- A) = (-A) + A= O. So
\- A is the additive inverse of A or negative of A.
ij-mxn


# 3.4.4 Properties of scalar multiplication of a matrix

If A = [a ] and B = [b ] be two matrices of the same order, say m x n, and k and I are
scalars, then

(i) k(A +B) = k A + KB, (ii) (k+l)A =kA+lA

(ii) k (A + B) = k ([a ] + [b]])
= k [a + b]] = [k (a + b)] = [(k a ) + (k bp)]
= [k a ] + [k b]] = k [a ] + k [b ] = kA + KB
(iii) (k + 1) A = (k + 1) [a]]
= [(k + 1) a]] + [k a ] + [l a ] = k [a ] + / [a ] = k A + 1 A
8 0
6

Example 8 If A = 4 -2 and B = 4 2
, then fi

3
-5
2 -2
1
find the matrix X, such that
2A +3X = 5B.

Solution We have 2A + 3X = 5B

or
2A +3X-2A=5B-2A
or
2A-2A+3X=5B-2A
0+3X = 5B-2A

or
or
3X = 5B-2A
1
3

(Matrix addition is commutative)
(-2A is the additive inverse of 2A)
(O is the additive identity)

or
Ou

X = (5B-2A)

2 -2

or

X =-
1
3
5

4

2
1
-2

. 4
3
8

0
6
2

=
1
3
10 -10

-16 0

20 10 + -8 4

-5

25

5

-6 -12

<!-- PageFooter="Reprint 2024-25" -->


================================================================================

<!-- PageNumber="48" -->
<!-- PageHeader="MATHEMATICS" -->

10-16 -10+0

1

1

0+4 = = 12 14 =4

3

20-8
-25-6 5-12

3

-6 -10
31
-7
-2

4
3
6

3

Example 9 Find X and Y, if X + Y =
5
0
2
9
and X - Y =
3
0 -1

Solution We have (X+ Y)+ (X-Y)=

5
0

2
9

\+

3
0

6
-1

or

(X + X) + (Y -Y) =

8
0
8
2X =
8
4
8
8
20804
\=

8
0
4

8
8

or

X =
1

Also

(X + Y)- (X -Y) =
X-Y)= 5 2]3 6
\-

0
-1

or

(X - X) + (Y + Y) =

0
9
5-3 2-6
0 9+1
1
1 2 -4 1 -2
2 0 10 -0 5
\=

2Y =
2 -4
0

10
or

Y =

Example 10 Find the values of x and y from the following equation:

7 2- 3 + 3 -4 7 6
2
x
74-3+1 215 14

Solution We have

x
27 y-3 + 1 2 - 15 14 - 14 29 -6 + 1 2 15 14
5
3 -4
7
6
2x
10
3
-4
7 6
\=
=

<!-- PageFooter="Reprint 2024-25" -->

14
3
10
3

-31 -7

ished

<!-- PageBreak -->

<!-- PageNumber="49" -->
<!-- PageHeader="MATRICES" -->

or

10-4
[
2x+3
14+1
2y-6+2

=

7
15 14
6

I

2x+3
15
6
2y-4

=

7
15
6
14

(Why?)


<table>
<tr>
<th>or</th>
<th>2x+3 =7</th>
<th>and</th>
<th>2y - 4 = 14</th>
</tr>
<tr>
<td>or</td>
<td>2x=7-3</td>
<td>and</td>
<td>2y =18</td>
</tr>
<tr>
<td>or</td>
<td>4 x = 2</td>
<td>and</td>
<td>18 y= 2</td>
</tr>
<tr>
<td>i.e.</td>
<td>x =2</td>
<td>and</td>
<td>y = 9.</td>
</tr>
</table>


Example 11 Two farmers Ramkishan and Gurcharan Singh cultivates only three
varieties of rice namely Basmati, Permal and Naura. The sale (in Rupees) of these
varieties of rice by both the farmers in the month of September and October are given
by the following matrices A and B.

September Sales (in Rupees)

Basmati

Permal

Naura

A =

[

10,000

20,000

30,000

Ramkishan

50,000

30,000

10,000

Gurcharan Singh

October Sales (in Rupees)

Basmati

Permal

Naura

B =
I

5000
20,000

10,000

6000

Ramkishan

10,000

10,000

Gurcharan Singh

(i) Find the combined sales in September and October for each farmer in each
variety.

(ii)
Find the decrease in sales from September to October.

(iii) If both farmers receive 2% profit on gross sales, compute the profit for each
farmer and for each variety sold in October.


# Solution

(i) Combined sales in September and October for each farmer in each variety is
given by

Basmati
L

30,000
40,000
Permal
Naura

36,000

Ramkishan

A + B =

15,000
70,000

20,000

Gurcharan Singh

<!-- PageFooter="Reprint 2024-25" -->


================================================================================

<!-- PageNumber="50" -->
<!-- PageHeader="MATHEMATICS" -->

(ii) Change in sales from September to October is given by

A -B=
I

Basmati
5000
30,000
2
100
Basmati
5000
20,000
Basmati

Permal

Naura

10,000

24,000

Ramkishan

Gurcharan Singh

(iii)
2% of B =

x B=0.02 ×B

Permal

Naura

= 0.02
1

10,000
Permal

Naura

=

[
400
100

200

120

Ramkishan

200

200

Gurcharan Singh

Thus, in October Ramkishan receives ₹ 100, ₹ 200 and ₹ 120 as profit in the
sale of each variety of rice, respectively, and Grucharan Singh receives profit of₹ 400,
₹ 200 and ₹ 200 in the sale of each variety of rice, respectively.


# 3.4.5 Multiplication of matrices

Suppose Meera and Nadeem are two friends. Meera wants to buy 2 pens and 5 story
books, while Nadeem needs 8 pens and 10 story books. They both go to a shop to
enquire about the rates which are quoted as follows:

Pen - ₹ 5 each, story book - ₹ 50 each.

How much money does each need to spend? Clearly, Meera needs ₹ (5 x 2+50 x 5)
that is ₹ 260, while Nadeem needs (8 x 5 + 50 x 10) ₹, that is ₹ 540. In terms of matrix
representation, we can write the above information as follows:

Requirements
Prices per piece (in Rupees) Money needed (in Rupees)

2

5

5

8 10

50

[

5×2+5×50
8×5+10×50
\=

260
540

Suppose that they enquire about the rates from another shop, quoted as follows:
pen - ₹ 4 each, story book - ₹ 40 each.

Now, the money required by Meera and Nadeem to make purchases will be
respectively ₹ (4 x 2+ 40 × 5) = ₹208 and ₹ (8 x 4 + 10 x 40) = ₹ 432

<!-- PageFooter="Reprint 2024-25" -->

20,000

0

1

10,000

6000
Ramkishan
10,000
1
Gurcharan Singh

We sled

<!-- PageBreak -->

<!-- PageNumber="51" -->
<!-- PageHeader="MATRICES" -->

Again, the above information can be represented as follows:

Requirements Prices per piece (in Rupees) Money needed (in Rupees)

2
8 10
]
5

4

40

[

4×2+40×5
8×4 +10×40
\=

208
432

Now, the information in both the cases can be combined and expressed in terms of
matrices as follows:

Requirements Prices per piece (in Rupees) Money needed (in Rupees)

2
8
5
5
10

5

50 40
4

=
!
cation */

5×2+5×50 4×2+40×5
8×5+10×50 8×4+10×40

260 208
540 432

The above is an example of multiplication of matrices. We observe that, for
multiplication of two matrices A and B, the number of columns in A should be equal to
the number of rows in B. Furthermore for getting the elements of the product matrix,
we take rows of A and columns of B, multiply them element-wise and take the sum.
Formally, we define multiplication of matrices as follows:

The product of two matrices A and B is defined if the number of columns of A is
equal to the number of rows of B. Let A = [a ] be an m x n matrix and B = [b ] be an
n xp matrix. Then the product of the matrices A and B is the matrix C of order m x p.
To get the (i, k)th element ca of the matrix C, we take the ith row of A and kth column
of B, multiply them elementwise and take the sum of all these products. In other words,
if A = [a ] > , B = [b ]]> >, then the ith row of A is [a, a. ... a ] and the kth column of

bık

b2k

B is

, then cu = a but ab2 + a 3 bak + ... + a b= Zaj bjk

b,

nk

ik-m × p

in
nk
n
j=1

The matrix C = [c ] >, is the product of A and B.

For example, if C =
0
1 -1 2
3
4

7

and D = - 1 1 |, then the product CD is defined
5 -4
2

<!-- PageFooter="Reprint 2024-25" -->


================================================================================

<!-- PageNumber="52" -->
<!-- PageHeader="MATHEMATICS" -->

2
4
-1
5 -4
1
This is a 2 x 2 matrix in which each
and is given by CD =
0
1 -1 2
3

entry is the sum of the products across some row of C with the corresponding entries
down some column of D. These four computations are

Entry in
first row
first column
0

1 -1 2
3

4

5

7
1 =
4
(1) (2) +(-1) (-1)+(2) (5)
?

?
?

Entry in
first row

1 -1 2

3

4

-1
5

2

1
4
7

=

13
?

(1) (7)+(-1) (1) +2 (-4)

second column
0
-1
3

?
Entry in
1
2
2
13
\=
0

second row
first column

-2
?
Entry in
1

second row
second column
0

-1
3

2
4

2
-1
5

7
1
4

=

13
17
0 (7) + 3(1) + 4 (-4)
2

Thus CD =

-2

13
17 -13
6
2

9
3

7 9 8

Example 12 Find AB, if A =
and B =
2 60
.

Solution The matrix A has 2 columns which is equal to the number of rows of B.
Hence AB is defined. Now

AB =
6(2)+9(7) 6(6)+9(9) 6(0)+9(8)
2(2) +3(7) 2(6) +3(9) 2(0) +3(8)

12+63 36+81 0+72

1

=
4+21 12+27 0+24

75
117
72
24 25 39 24
\=

<!-- PageFooter="Reprint 2024-25" -->

-1
5
7
1
4
0 (2) + 3(-1) + 4 (5)

4

2

-1

7

<!-- PageBreak -->

<!-- PageNumber="53" -->
<!-- PageHeader="MATRICES" -->

Remark If AB is defined, then BA need not be defined. In the above example, AB is
defined but BA is not defined because B has 3 column while A has only 2 (and not 3)
rows. If A, B are, respectively mx n, k x ] matrices, then both AB and BA are defined
if and only if n = k and / = m. In particular, if both A and B are square matrices of the
same order, then both AB and BA are defined.


# Non-commutativity of multiplication of matrices

Now, we shall see by an example that even if AB and BA are both defined, it is not
necessary that AB = BA.

Example 13 If A =

1 -2 3
-4 2 5

2 3

and B= 4 5 , then find AB, BA. Show that

2 1

AB # BA.

Solution Since A is a 2 × 3 matrix and B is 3 × 2 matrix. Hence AB and BA are both
defined and are matrices of order 2 × 2 and 3 × 3, respectively. Note that

AB =
4
1 -2
2
3
5
2 3

2-8+6 3-10+3
-8+8+10 -12+10+5 ||10 3
\=
4 5
2 1
\=
0
-4
2 3
1 -2 3
4 5
4-20
2 1
4
2
5
E
JE

and
BA =

2-12 -4+6 6+15
-8+10
2-4 -4+2 6+5
\=

-10
-16

21
\=
37
12+ 25
-2 -2 11
2
2

Clearly AB # BA

In the above example both AB and BA are of different order and so AB # BA. But
one may think that perhaps AB and BA could be the same if they were of the same
order. But it is not so, here we give an example to show that even if AB and BA are of
same order they may not be same.

Example 14 If A =

1
0
and B =
0
10
1

then AB =

0
-1 0
1

and

BA =

-1
0
)
0
Clearly AB # BA.

Thus matrix multiplication is not commutative.

<!-- PageFooter="Reprint 2024-25" -->


================================================================================

<!-- PageNumber="54" -->
<!-- PageHeader="MATHEMATICS" -->

Note This does not mean that AB # BA for every pair of matrices A, B for
which AB and BA, are defined. For instance,

IF A-[ 2] B-[3 ]
0
?

0
4
then AB = BA =
3
8
0
Observe that multiplication of diagonal matrices of same order will be commutative.


# Zero matrix as the product of two non zero matrices

We know that, for real numbers a, b if ab = 0, then either a = 0 or b = 0. This need
not be true for matrices, we will observe this through an example.

0

Example 15 Find AB, if A =

0

-1
2
and B =

3 5
00
.

0 -13 5

Solution We have AB =
AB- 0 2 0 0 0 0
\=

Thus, if the product of two matrices is a zero matrix, it is not necessary that one of
the matrices is a zero matrix.


# 3.4.6 Properties of multiplication of matrices

The multiplication of matrices possesses the following properties, which we state without
proof.

1\. The associative law For any three matrices A, B and C. We have
(AB) C = A (BC), whenever both sides of the equality are defined.

2\. The distributive law For three matrices A, B and C.

(i) A (B+C) = AB + AC

(ii) (A+B) C=AC + BC, whenever both sides of equality are defined.

3\. The existence of multiplicative identity For every square matrix A, there
exist an identity matrix of same order such that IA = AI = A.

Now, we shall verify these properties by examples.

Example 16 If A = 2 0 3 , B= 0 2 and C = , find
1 2 3 -4
3 -1 2 -14
1 1 -1] [13
2 0 -2 1

A(BC), (AB)C and show that (AB)C = A(BC).

<!-- PageFooter="Reprint 2024-25" -->
<!-- PageBreak -->

<!-- PageNumber="55" -->
<!-- PageHeader="MATRICES" -->

1+0+1 3+2-4
3+0-2 9-2+8
Solution We have AB = 2 0 3 02 = 2+0-3 6+0+12 =- 1 18
1 1 -1 13
3 -1 2-14
1
2
1
15

2+2
4+0 6-2 -8+1
1+30 2+0 3-30 -4+15

(AB) (C)= - 1 18 - = - 1+36 -2+0 -3-36 4+18
2
1 2 3 -4
15
1
2 0 -2 1
1
4 4 4 -7
\=
35 -2 -39 22
31 2 -27 11
13
1
2
2 0 -2 0+4 0+0 0-4 0+2
3
1||
4
-1+8 -2+0 -3-8 4+4
1+6 2+0 3-6 -4+3
☒

=

Now
BC =
0 2
-1 4
7 2 -3 -1 7
☒

Therefore
(BC) = 2 0 3 4 0 -4 2

4 0 -4 2
7 -2 -11 8
1 1 -1 7 2 -3 -1
3 -1
7+4-7 2+0+2 -3-4+11 -1+2-8
\=
14+0+21 4+0-6 -6+0-33 -2+0+24
21-4+14 6+0-4 -9+4-22 -3-2+16
☒
2
7 -2 -11 8

4 4 4 -7

=
35 -2 -39 22
31 2 -27 11

Clearly, (AB) C = A (BC)

<!-- PageFooter="Reprint 2024-25" -->

not to be replaenshed


================================================================================

<!-- PageNumber="56" -->
<!-- PageHeader="MATHEMATICS" -->

0

6

7

0
1
1
2

Example 17 If A = - 6 0 8 ,B=1 02,C =- 2

7-80 12 C=3

Solution Now, A+B= - 5 0 10

So
(A+B)C= - 5 0 10 -2 =- 10+0+30 = 20

Further

Calculate AC, BC and (A + B)C. Also, verify that (A + B)C = AC + BC
0
7
8
8 -6 0
0
7
8
0
6
7
2
3
2
AC= - 6 0 8 -2 =- 12+0+24 = 12
3
2
102 -2 =2+0+6 = 8
3
0-14+24
16+12+0
0-12+21
14+16+0
0-2+3
1
-2
2
10
28
9
30
8 -6
0
7 -8 0
0
1
2
1
0
2-4+0
1
9
1
10
8
-2
12
20
28
\=
30
+

šhed

and
BC =

So
AC + BC =

Clearly,

1
(A + B) C = AC + BC
2
3
1
2

Example 18 If A = 3 -2 1 , then show that A3 - 23A - 40 I = O
4

3
1
2
3
19
4
8
Solution We have A2 = A.A = 3 -2 1 3 -2 1 = 1 12 8
1
2

4 2 1 4 2 1 14 6 1

15

<!-- PageFooter="Reprint 2024-25" -->
<!-- PageBreak -->

<!-- PageNumber="57" -->
<!-- PageHeader="MATRICES" -->

2
8
63
So
13 = A A2 = 3 -2 1 1 12 8 = 69 -6 2
1
4 2 1 14 6 15 92 46

3
19
4

1
3
-2
3
1
-69

40
0
0
1

0

0
0
1

-6 23 + -69 46 -23 + 0 -40 0

-40
0

=

0
000

Example 19 In a legislative assembly election, a political group hired a public relations
firm to promote its candidate in three ways: telephone, house calls, and letters. The
cost per contact (in paise) is given in matrix A as

Cost per contact

A =

100
50
40

Telephone
Housecall
Letter

The number of contacts of each type made in two cities X and Y is given by

Telephone

Housecall
Letter

B=

1000
3000

500 5000 |->X

1000
10,000
\>Y
Find the total amount spent by the group in the two
cities X and Y.

<!-- PageFooter="Reprint 2024-25" -->

46
69
23
63
Now

A3 - 23A -40I =
69
92
63
\=
69
92

09 6 23 -23 2 -40 0 1 0
63 46 69
2
23
1
1
0
40
0
0
0
69-69+0
2
46
6
23
46
46
46
63
4
-23
-92 -46 -23
46-46+0
-6+46-40 23-23+0
69
63
63-23-40
69-69+0
92-92+0
46-46+0
63-23-40
0
0
=000=0

como total repair so


================================================================================

<!-- PageNumber="58" -->
<!-- PageHeader="MATHEMATICS" -->

Solution We have

BA =

120,000 + 100,000 +500,000
340,000 -> X
\=
1
40,000 + 50,000 + 250,000

-> X
-> Y

720,000
-> Y

So the total amount spent by the group in the two cities is 340,000 paise and
720,000 paise, i.e., ₹ 3400 and ₹ 7200, respectively.


# EXERCISE 3.2

1\. Let A =
,

3

4
2 B - 2 5 C = 3 4
1
3
-2
,

Find each of the following:

(i) A + B

(ii) A - B

(iii) 3A - C

(iv) AB

(v) BA

2\. Compute the following:

b

a
b

b
a

(i)
(ii)
-b
a
+
-1 4 -612 7 6
2 (iv) COS2.
a

cos x
sin2

sin2 x

2
sin2 x

cos2 x
2

(iii) 8 5 16 + 8 0 5 (IV) |2 x
2
8
5
3
2
b
4
1
a
a

(i)

-b

a

b

b
a

(ii)

2
3

[2 3 4]
(iii)

2
1 -2
3

2

1

1

iv) 3 4 5 0 2 4
4 5 6

2

-3

(vi)

3 -1 3
-1 0 2

1

3

1
0

CERT

a2 + b2 b2 + c2
a2 + c2

a2 + b2

\+

2ab 2bc
-2ac -2ab

\+

cos2 x
2

3\. Compute the indicated products.

cos2 x sin2 x
2
3
1
2
3
1

2
3 41 -3 5
3
0
5

(v)

-11
3 2

1
-1

0
2
1

<!-- PageFooter="Reprint 2024-25" -->

bashed

2

<!-- PageBreak -->

<!-- PageNumber="59" -->

MATRICES
3 -1 2
4
1
2
2
4. If A = 5 0 2 ,B= 4 2 5 andC= 0 3 2 , then compute
1
2 -3
1 -1 1
2
3
2
4
3

1
-2
3
(A+B) and (B- C). Also, verify that A + (B- C) = (A +B) - C.

5\. If A =
1
7
3
3

1
3

5
3
2
3
2
cos e
sin 0
cos O
\+ sin0

and B=

0
2
5
1
5
7
5

3
3
5
5
6
5
2

1
5

4
then compute 3A - 5B.
,

6\. Simplify cose
I
-sin 0

-cos ℮
sin ℮
7. Find X and Y, if

(i) X + Y =
7
0
5
2
and X - Y =

(ii) 2X +3Y =
2
4
and 3X + 2Y =

3
0

2
2
1
5

8\. Find X, if Y =
1

2

3
and 2X + Y =

1
3

0
2

9\. Find x and y, if 2
0

=

1

5
6
8

10\. Solve the equation for x, y, z and t, if 2
y
:
x
Z
t

+3
1
-1

0 2 -3 3 5
6

11\. If x
3
\+ y
-1
1

[3]+[H]-[9]
\=

5
find the values of x and y.
\>

12\. Given 3
x
y
Z
W

=

-1

x 6
2w
+

4

z+W

x+y
3

、

\>

find the values of x, y, z and w.

<!-- PageFooter="Reprint 2024-25" -->

2
5
sin ℮
cos ℮
3
0
3
0

1
3
+
x
wb jppublished

4

y
1

0
2


================================================================================

<!-- PageNumber="60" -->
<!-- PageHeader="MATHEMATICS" -->

COS x

0
1

-sin x
COS x
0
, show that F(x) F(y) = F(x + y).

13\. If F (x) =
sin x
0
0
14\. Show that
5 -1 21 2 1 5 -1

(i)
6 7 3 4 3 4 6 7
¥

[1 2 3][-1 1 0] [-1 1 0][1 2 3]
(ii) 0 1 0 0 -1 1 / 0-1 1 01 0
1 10 2 34 234110
2 0
1

15\. Find A2 - 5A + 6I, if A = 2 1 3

1 -1 0
102
2 0 3
-2

16\. If A = 0 2 1 , prove that A3 - 6A2 + 7A + 21 = 0

1
0
, find k so that A2 = kA - 2I
17. If A =
and I=

0

18\. If A =

\- tan
0
a

2
and I is the identity matrix of order 2, show that

tan

I +A = (I-A)
cosa
-sin a
sina cosa
I

19\. A trust fund has ₹ 30,000 that must be invested in two different types of bonds.
The first bond pays 5% interest per year, and the second bond pays 7% interest
per year. Using matrix multiplication, determine how to divide ₹ 30,000 among
the two types of bonds. If the trust fund must obtain an annual total interest of:
(a) ₹1800
(b) ₹2000

<!-- PageFooter="Reprint 2024-25" -->

0
a
2
. .. . bemder Published

1

3
4 -2

<!-- PageBreak -->

<!-- PageNumber="61" -->
<!-- PageHeader="MATRICES" -->

20\. The bookshop of a particular school has 10 dozen chemistry books, 8 dozen
physics books, 10 dozen economics books. Their selling prices are ₹ 80, ₹60 and
₹ 40 each respectively. Find the total amount the bookshop will receive from
selling all the books using matrix algebra.

Assume X, Y, Z, W and P are matrices of order 2 × n, 3 x k, 2 xp, n × 3 and p x k,
respectively. Choose the correct answer in Exercises 21 and 22.

21\. The restriction on n, k and p so that PY + WY will be defined are:
(A) k = 3, p=n
(B) k is arbitrary, p = 2

(C) p is arbitrary, k = 3
(D) k=2, p=3

22\. If n = p, then the order of the matrix 7X - 5Z is:
(A) p ×2
(B) 2 × n
(C) n × 3
(D) p × n


# 3.5. Transpose of a Matrix

In this section, we shall learn about transpose of a matrix and special types of matrices
such as symmetric and skew symmetric matrices.

Definition 3 If A = [a ] be an m × n matrix, then the matrix obtained by interchanging
the rows and columns of A is called the transpose of A. Transpose of the matrix A is
denoted by A' or (AT). In other words, if A = [a ]x,, then A' = [a ]]> „. For example,

if A = 3 1
0
3

5
-1
5 3 x 2
,
then A' =

5
3 3 0
1

5
-1
2× 3
alexaENved


## 3.5.1 Properties of transpose of the matrices

We now state the following properties of transpose of matrices without proof. These
may be verified by taking suitable examples.

For any matrices A and B of suitable orders, we have

(i) (A')' = A,
(ii) (kA)' = kA' (where k is any constant)

(iii) (A + B)' = A' + B'

(iv) (AB)' = B' A'

Example 20 If A =
4
3 V3 2
2

0
and B =
1
2 -1 2
2
4
verify that
\>

(i) (A')' = A,
(ii) (A + B)' = A' + B',

(iii) (KB)' = kB', where k is any constant.

<!-- PageFooter="Reprint 2024-25" -->


================================================================================

<!-- PageNumber="62" -->
<!-- PageHeader="MATHEMATICS" -->


# Solution

(i)
We have

= 3 V3 =>A'= V3 2 =>(A' = 3 V3 = A
2
4 2 0
2

4
2

0

Thus (A')' = A

(ii)
We have

A =

4
3 3 2
0
,

2
2
1
-1
2 4
=>A+B=
5
5 3-1 4
4
4

Therefore

(A + B)' =

5
V3 -1
4
3
2

5
4
4

Now

A' =

3 2 ,B'= - 12
\>

,

2
4

So

A' + B' = 3

Thus

(A + B)' = A' + B'

(iii)
We have

kB =

1

2

4

k

k 4k
2k

Then

KB)' = | -k 2k = k -1 2 = kB'

Thus

2k k
2k 4k
(kB)' = kB'

3
2

4

0

4
0
5
5
3-1 4
4 4

2 1
not tasomph

k 2 -1 2 2k -k 2k

=

2 4
2 1

<!-- PageFooter="Reprint 2024-25" -->
<!-- PageBreak -->

<!-- PageNumber="63" -->
<!-- PageHeader="MATRICES" -->

Example 21 If A = | 4 ,B=[1 3 -6], verify that (AB)' = B'A'.
-2
5
Solution We have
-2

A = 4 , B=[1 3 -6]
5
-2
5

then

AB = 4 1 3 -6] = 4 12 -24

Now

A' = [-2 4 5] , B'=

-2 -6 12
5 15 -30
1
3
-6
-2
4
5
12 -24 -30

B'A' = 3 [-2 4 5]= - 6 12 15 =(AB)
1
-6

Clearly (AB)' =B'A'


## 3.6 Symmetric and Skew Symmetric Matrices

Definition 4 A square matrix A = [a ] is said to be symmetric if A' = A, that is,
[a ] = [a ] for all possible values of i and j.

For example A = 2 -1.5 -1 |is a symmetric matrix as A' = A
3 -1 1
V3 2 3

Definition 5 A square matrix A = [a ] is said to be skew symmetric matrix if
A' =- A, that is a =- a , for all possible values of i and j. Now, if we put i = j, we
have a = - a . Therefore 2a = 0 or a = 0 for all i's.

This means that all the diagonal elements of a skew symmetric matrix are zero.

<!-- PageFooter="Reprint 2024-25" -->


================================================================================

<!-- PageNumber="64" -->
<!-- PageHeader="MATHEMATICS" -->

For example, the matrix B =
-e
0

-f -g 0
0

e
☒
g
f
is a skew symmetric matrix as B'= - B
☒

Now, we are going to prove some results of symmetric and skew-symmetric
matrices.

Theorem 1 For any square matrix A with real number entries, A + A' is a symmetric
matrix and A - A' is a skew symmetric matrix.

Proof Let B = A + A', then

B' = (A + A')'
= A' + (A')' (as (A + B)' = A' + B')
= A' + A (as (A')' = A)
= A + A' (as A + B = B+A)
= B
B = A + A' is a symmetric matrix
C = A - A'
C' = (A - A')' = A' - (A')' (Why?)
= A' - A (Why?)
= - (A - A') =- C
☒ ☒ ☒

Therefore

Now let

Therefore
C = A -A' is a skew symmetric matrix.

Theorem 2 Any square matrix can be expressed as the sum of a symmetric and a
skew symmetric matrix.

Proof Let A be a square matrix, then we can write

A =- (A +A') + +(A-A')
2
1

1
2

From the Theorem 1, we know that (A + A') is a symmetric matrix and (A - A') is

1

a skew symmetric matrix. Since for any matrix A, (kA)' = kA', it follows that - (A + A')

2

<!-- PageFooter="Reprint 2024-25" -->
<!-- PageBreak -->

<!-- PageNumber="65" -->
<!-- PageHeader="MATRICES" -->

1

is symmetric matrix and - (A-A') is skew symmetric matrix. Thus, any square
5
matrix can be expressed as the sum of a symmetric and a skew symmetric matrix.

Example 22 Express the matrix B= - 1 3 4 |as the sum of a symmetric and a

2 -2 -4
1 -2 -3

skew symmetric matrix.

Solution Here

2 -1 1

B'= - 2 3 -2
-4 4 -3

1

Let

P= = (B +B') =- - 3 6 2 =-

,

2

2

Now

P'

2
-3
-3
2

1
2
2
3
1
3
4
-3
-3
2

3
2

2
3
3
3
6
-3
2
2
-3
2
1

Thus

-1

Also, let

Q=(B-B)-1 1 0 6 = 1 0

0 -1 -5
5
-6 0

2
2
0
5

2
-3
-5
2

3
0

hed

3
-3
2

1
-3

= P
1
not szerep
P= = (B+B') is a symmetric matrix.
1
2

<!-- PageFooter="Reprint 2024-25" -->


================================================================================

<!-- PageNumber="66" -->
<!-- PageHeader="MATHEMATICS" -->

0

2
3
1

5
0

3

Then
Q' = 2 0 -3 =- Q

-1
2
-5
2
1
(B-B') is a skew symmetric matrix.

Thus

Q=

2
2
2
-3
3
2
3
1
-3
2

1
-3
-3
2

\+

1
5
0

0

2
2

3

3
0
-1
1

-2
-2 -3
-4

3
4 =B

Thus, B is represented as the sum of a symmetric and a skew symmetric matrix.


# EXERCISE 3.3

1\. Find the transpose of each of the following matrices:

5

1

(i)

11\)

1
2
-1
3

(iii)

-1
5
V3 5 6
6

2 3 -1

2\. If A = 5 7 9 and B=| 1 2 0 , then verify that
-2
1
1
1
1

(i) (A + B)' = A' + B',
3 4
1

3\. If A'= - 1 2 and B =
0

-1 2 1
123
,
then verify that

(i) (A + B)' = A' + B'

(ii) (A - B)' = A' - B'

-1

2

-5
2

2

Now

P +Q=

2

-1
-1
2
3

-4 1 -5
3

(ii) (A - B)' = A' - B'

<!-- PageFooter="Reprint 2024-25" -->
<!-- PageBreak -->

<!-- PageNumber="67" -->
<!-- PageHeader="MATRICES" -->

4\. If A' =
and B=
-2 3
1
-1 0
1
2

,
then find (A + 2B)'

5\. For the matrices A and B, verify that (AB)' = B'A', where

2
1

0
2

6\. If (i) A =

(i) A= 4 , B=[-1 2 1] (ii) A= 1 , B=[1 5 7]
3
cosa sina
-sina cosa
,
then verify that A' A = I

(ii) If A =
-cosa
5
[
sina cosa
sin a
1
5
-1
1

1
then verify that A' A = I
,

7\.
(i) Show that the matrix A = - 1

2
1
is a symmetric matrix.

3

0
1 -1

(ii) Show that the matrix A = - 1 0 1 |is a skew symmetric matrix.

1 -1 0

8\. For the matrix A =
1
5
, verify that

6

(i) (A + A') is a symmetric matrix

(ii) (A - A') is a skew symmetric matrix

1

0 a b

9\. Find -(A+A') and -(A-A'), when A = - a 0 c
1
2
2

-b -c 0

7
Von meine Shed

10\. Express the following matrices as the sum of a symmetric and a skew symmetric
matrix:

<!-- PageFooter="Reprint 2024-25" -->


================================================================================

<!-- PageNumber="68" -->
<!-- PageHeader="MATHEMATICS" -->

(i) |1 -1
1
3

5

(ii)
-2 3 -1
2 -1 3
6 -2 2

3

(iii)

-2 -2 1

-4

-5
3

-1
2

(iv)

-1
2

Choose the correct answer in the Exercises 11 and 12.

11\. If A, B are symmetric matrices of same order, then AB - BA is a

(A) Skew symmetric matrix

(B) Symmetric matrix

(C) Zero matrix

(D) Identity matrix

12\. If A =
cosa
sin a

-sin a
cosa
π
6

,and A + A' = I, then the value of a is

(A)

(B)
π
3

(C) π

(D)

3T
2


# 3.7 Invertible Matrices

Definition 6 If A is a square matrix of order m, and if there exists another square
matrix B of the same order m, such that AB = BA = I, then B is called the inverse
matrix of A and it is denoted by A-1. In that case A is said to be invertible.

For example, let

A =

2
1 2
3
and B =

-1 2
2 -3
be two matrices.

Now

AB =

2 3][ 2 -3
12 -12

=

4-3 -6+6
2 - 2 - 3 +4 -0 1 = 1

1
]=]
\=

Also
BA =
1
0 1
0
= I . Thus B is the inverse of A, in other
words B = A-1 and A is inverse of B, i.e., A = B-1

<!-- PageFooter="Reprint 2024-25" -->

1 5

<!-- PageBreak -->

<!-- PageNumber="69" -->
<!-- PageHeader="MATRICES" -->


# Note

1\. A rectangular matrix does not possess inverse matrix, since for products BA
and AB to be defined and to be equal, it is necessary that matrices A and B
should be square matrices of the same order.

2\. If B is the inverse of A, then A is also the inverse of B.

Theorem 3 (Uniqueness of inverse) Inverse of a square matrix, if it exists, is unique.
Proof Let A = [a ] be a square matrix of order m. If possible, let B and C be two
inverses of A. We shall show that B = C.

Since B is the inverse of A

AB = BA = I
... (1)

Since C is also the inverse of A

AC = CA = I
... (2)

Thus

B = BI = B (AC) = (BA) C=IC= C

Theorem 4 If A and B are invertible matrices of the same order, then (AB)-1 = B-1 A-1.

Proof From the definition of inverse of a matrix, we have

(AB) (AB)-1 = 1

or
A-1 (AB) (AB)-1 = A-1I
or
(A-1A) B (AB)-1 = A-1
or
IB (AB)-1 = A-1
or
or
Hence
☒
or
B-1 B (AB)-1 = B-1 A-1
I (AB)-1 = B-1 A-1
(AB)-1 = B-1 A-1

(Pre multiplying both sides by A-1)
(Since A-1 I = A-1)


# EXERCISE 3.4

1\. Matrices A and B will be inverse of each other only if

(A) AB = BA (B) AB = BA = 0

(C) AB = 0, BA = I (D) AB = BA = I

<!-- PageFooter="Reprint 2024-25" -->


================================================================================

<!-- PageNumber="70" -->
<!-- PageHeader="MATHEMATICS" -->


# Miscellaneous Examples

Example 23 If A =

cose sin
-sin 0 cose
\>
then prove that A" =
cosne
-sinne cosne
sin ne
, ne N.

Solution We shall prove the result by using principle of mathematical induction.

We have
P(n) : If A =

[
cose sin ℮
-sin 0 cose
›

then A" =

cosne
-sinne cosne
sin ne

,nEN

P(1) : A =
[
cose sin ℮
-sin ℮ cose

1
, so A =

sin ℮
cose sin ℮
cos O

Therefore,
the result is true for n = 1.

Let the result be true for n = k. So

P(k) : A =
[

cose sin ℮
-sin 0 cose
, then Ak =

laned

coske sinko
-sinke coske
1

Now, we prove that the result holds for n = k +1

Now

Ak+ 1 = A · AK =
sin ke
-sin 0 cose
cose sine coske
-sin ke coske
cos O cos ke - sin Osin ke
cos Osin ke + sin Ocos ke
sin Ocos k0 + cos Osin ke
-sin Osin ke + cos 0 cos ke

=
I

cos (0+ k0)
\=
sin (0+k0) cos(0+k0)
cosn 0

sin (0+ k0)

\-
=
cos (k +1)0
sin (k +1)0

sin (k +1)0
cos (k +1)0

sinn 0
I
Therefore, the result is true for n=k + 1. Thus by principle of mathematical induction,
we have A"
-sinne cosne
,
holds for all natural numbers.

Example 24 If A and B are symmetric matrices of the same order, then show that AB
is symmetric if and only if A and B commute, that is AB = BA.

Solution Since A and B are both symmetric matrices, therefore A' = A and B' = B.

<!-- PageFooter="Reprint 2024-25" -->
<!-- PageBreak -->

<!-- PageNumber="71" -->
<!-- PageHeader="MATRICES" -->

Let
AB be symmetric, then (AB)' = AB
But
Therefore

(AB)' = B'A'= BA (Why?)

BA = AB

Conversely, if AB = BA, then we shall show that AB is symmetric.

Now

(AB)' = B'A'
= B A (as A and B are symmetric)
= AB

Hence AB is symmetric.

Example 25 Let A =
,

-3 -1 B-52.C=13 8
4

7
,
Find a matrix D such that
4
CD - AB = O.

Solution Since A, B, C are all square matrices of order 2, and CD - AB is well
defined, D must be a square matrix of order 2.

Let
D =
c d
Then CD - AB = 0 gives

a

b

\-
3
2 5 ab 2 -152
8
d
= 0
3
4
7
4
C
2a+5c 2b+5d
3
Ba+ 80 36 +80 43 2 0 0
0
0
0
\=

or

0
0

or

1

2a+5c-3
2b+ 5d
3a+8c-43 3b+8d -22
2a + 5c-3 = 0
3a + 8c - 43 = 0
2b + 5d= 0
3b + 8d -22 = 0

By equality of matrices, we get

=
0 0
... (1)

and

... (2)
... (3)
... (4)

Solving (1) and (2), we get a =- 191, c=77. Solving (3) and (4), we get b =- 110,
d = 44.

<!-- PageFooter="Reprint 2024-25" -->


================================================================================

<!-- PageNumber="72" -->
<!-- PageHeader="MATHEMATICS" -->

Therefore

D =

a b
C
d
-191
-7 4
1


# Miscellaneous Exercise on Chapter 3

1\. If A and B are symmetric matrices, prove that AB - BA is a skew symmetric
matrix.

2\. Show that the matrix B'AB is symmetric or skew symmetric according as A is
symmetric or skew symmetric.

3\. Find the values of x, y, z if the matrix A = x y -z |satisfy the
equation
x -y
Z
A'A = I.

1
2 07
2
0

2y
Z

4\. For what values of x : [1 2 1] 2 0 1 2 = C

1

0

0
O?

x

5\. If A =
-1
3
,show that A2 - 5A + 7I = 0.
\>

1
2
102x
0

6\. Findx, if [x -5 -1] 0 2 1 4=0

2

3
1

7\. A manufacturer produces three products x, y, z which he sells in two markets.
Annual sales are indicated below:


<table>
<tr>
<th>Market</th>
<th colspan="3">Products</th>
</tr>
<tr>
<td>I</td>
<td>10,000</td>
<td>2,000</td>
<td>18,000</td>
</tr>
<tr>
<td>II</td>
<td>6,000</td>
<td>20,000</td>
<td>8,000</td>
</tr>
</table>


<!-- PageFooter="Reprint 2024-25" -->

-110

<!-- PageBreak -->

<!-- PageNumber="73" -->
<!-- PageHeader="MATRICES" -->

(a) If unit sale prices of x, y and z are ₹ 2.50, ₹ 1.50 and ₹ 1.00, respectively,
find the total revenue in each market with the help of matrix algebra.

(b) If the unit costs of the above three commodities are ₹ 2.00, ₹ 1.00 and
50 paise respectively. Find the gross profit.

8\. Find the matrix X so that X
☒
456246
=

1 2 3 -7 -8 -9

Choose the correct answer in the following questions:

9\. If A =
a

is such that A2 = I, then
-a

(A) 1 +2 + By=0
(C) 1 - a2 - By = 0

(B) 1 - a2 + By = 0
(D) 1 + a2- By = 0

10\. If the matrix A is both symmetric and skew symmetric, then

(A) A is a diagonal matrix
(B) A is a zero matrix

(C) A is a square matrix

11\. If A is square matrix such that A2 = A, then (I + A)3 - 7 A is equal to

(A) A
(B) I-A
(C) I
(D) 3A

(D) None of these
Summary
E
Ean.

A matrix is an ordered rectangular array of numbers or functions.

A matrix having m rows and n columns is called a matrix of order m x n.

[a ]mx 1 is a column matrix.

[a]]] x, is a row matrix.

An m x n matrix is a square matrix if m = n.

A = [a ]mxm is a diagonal matrix if a; = 0, when i ± j.

A = [a ] , is a scalar matrix if a = 0, when i + j, a = k, (k is some
ij-n xn
constant), when i = j.

A =[a ]x, is an identity matrix, if a = 1, when i = j, a = 0, when i + j.

A zero matrix has all its elements as zero.

A = [a ] = [b ] = B if (i) A and B are of same order, (ii) an = ba for all
possible values of i and j.

<!-- PageFooter="Reprint 2024-25" -->


================================================================================

<!-- PageNumber="74" -->
<!-- PageHeader="MATHEMATICS" -->

KA = k[a ]mx n = [k(a )]_x
m xn

-A = (-1)A

A - B = A + (-1) B

A+B=B +A

(A + B) + C = A + (B +C), where A, B and Care of same order.

k(A + B) = kA + kB, where A and B are of same order, k is constant.

(k + l) A = kA + IA, where k and / are constant.

If A = [a ] x, and B = [bik]n xp, then AB = C = [Cuk]m xp> where Cik=Zajbjk
n

j=1

(i) A(BC) = (AB)C, (ii) A(B+C)=AB +AC, (iii) (A+B)C=AC+BC

If A = [a ]
ij-mxnº

then A' or AT = [a ],
ji-nx m

(i) (A')'=A, (ii) (kA)'=kA', (iii) (A+B)'=A'+B', (iv) (AB)' =B'A'

A is a symmetric matrix if A' = A.

A is a skew symmetric matrix if A' = - A.

Any square matrix can be represented as the sum of a symmetric and a
skew symmetric matrix.

If A and B are two square matrices such that AB = BA = I, then B is the
inverse matrix of A and is denoted by A-1 and A is the inverse of B.

Inverse of a square matrix, if it exists, is unique.

not to be s unique

<!-- PageFooter="Reprint 2024-25" -->
<!-- PageBreak -->


# NOTES

NCERT
not to be republished

<!-- PageFooter="Reprint 2024-25" -->


================================================================================

