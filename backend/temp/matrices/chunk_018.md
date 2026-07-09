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
