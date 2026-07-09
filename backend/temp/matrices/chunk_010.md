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
