## Validating Different Types of PIIs

Obviously the functions in `PiiDetector.py` are actually simplified versions of how you'd actually detect some of the PIIs. So I'll just make it clear here.

- SSN: The SSN functionality is actually implemented quite well. SSN is always in the form AAA-BB-CCCC. Of course whether this SSN corresponds to a real person or not is irrelevant, and keeping this simplified format maintains coverage whilst not needing someone to know the specific rules for the digits of the SSNs.
- Credit cards aren't always 16 digits, but a lot of them are. As well as this, a lot of credit and debit cards use Luhn's algorithm, which is a simple math algorithm used to see if the numbers on the card form a syntactically valid sequence. Whether that card corresponds to an active card is another matter. A lot of websites should be using Luhn's algorithm as a form of forward checking to minimize erroneous requests to payment gateways like Stiripe.
- Bank routing numbers: American routing numbers are typically a 9 digit sequence (**aka MICR routing number format**) that follow special rules to dictate which numbers need to go where. It's a format that involves some mathematics and specific rules what digits could be in a given slot, so using a regex isn't really the right call. This is a little more complex and takes awway from core features, and the reward isn't high for the project and context it's being used in.
- Bank account numbers: Arbitrary legnth and value, as its defined by the individual bank. You can't really validate it without checking the specific bank in question. 
  1. Overall, could be from 6 to 17 digits
  2. 8-12 digits is a common range
  3. only digits
  4. Based on sample data, we can do 12-17 digits I guess?

## Credits
- [SSN (See Structure Section) - Wikpedia](https://en.wikipedia.org/wiki/Social_Security_number#Structure)

- [Luhn's Algorithm in Python - teclado](https://teclado.com/30-days-of-python/python-30-day-9-project/)
- [Luhn's Algorithm - Wikipedia](https://en.wikipedia.org/wiki/Luhn_algorithm)

- [Bank Account Numbers](https://stackoverflow.com/questions/1540285/united-states-banking-institution-account-number-regular-expression)
- [American Bank Routing Numbers and ABA - Wikipedia](https://en.wikipedia.org/wiki/ABA_routing_transit_number)
- [Bank Routing Number Look Up Site](https://www.routingnumber.com/)