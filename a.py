def fact1(n):
    if n < 0:
        raise ValueError("\nFactorial is not defined for negative numbers\n")
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result

def fact2(n):
    result = 1
    for i in range(1, n + 1):
        result = result * i
    return result

print(fact1(5))
print(fact2(5))
