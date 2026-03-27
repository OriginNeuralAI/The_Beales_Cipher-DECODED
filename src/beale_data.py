"""
Beale Ciphers - Raw Data Module
Shared constants imported by all analysis scripts.

Source: Ward pamphlet (1885), public domain.

Phase 2: Includes BEALE_DOI_OFFSET mapping, reconstructed from B2
cipher + known plaintext via Needleman-Wunsch alignment.
"""

import re

# Beale Cipher 1 (Location) - 520 numbers, unsolved
B1_CIPHER = [
    71, 194, 38, 1701, 89, 76, 11, 83, 1629, 48, 94, 63, 132, 16, 111, 95, 84, 341, 975, 14,
    40, 64, 27, 81, 139, 213, 63, 90, 1120, 8, 15, 3, 126, 2018, 40, 74, 758, 485, 604, 230,
    436, 664, 582, 150, 251, 284, 308, 231, 124, 211, 486, 225, 401, 370, 11, 101, 305, 139, 189, 17,
    33, 88, 208, 193, 145, 1, 94, 73, 416, 918, 263, 28, 500, 538, 356, 117, 136, 219, 27, 176,
    130, 10, 460, 25, 485, 18, 436, 65, 84, 200, 283, 118, 320, 138, 36, 416, 280, 15, 71, 224,
    961, 44, 16, 401, 39, 88, 61, 304, 12, 21, 24, 283, 134, 92, 63, 246, 486, 682, 7, 219,
    184, 360, 780, 18, 64, 463, 474, 131, 160, 79, 73, 440, 95, 18, 64, 581, 34, 69, 128, 367,
    460, 17, 81, 12, 103, 820, 62, 116, 97, 103, 862, 70, 60, 1317, 471, 540, 208, 121, 890, 346,
    36, 150, 59, 568, 614, 13, 120, 63, 219, 812, 2160, 1780, 99, 35, 18, 21, 136, 872, 15, 28,
    170, 88, 4, 30, 44, 112, 18, 147, 436, 195, 320, 37, 122, 113, 6, 140, 8, 120, 305, 42,
    58, 461, 44, 106, 301, 13, 408, 680, 93, 86, 116, 530, 82, 568, 9, 102, 38, 416, 89, 71,
    216, 728, 965, 818, 2, 38, 121, 195, 14, 326, 148, 234, 18, 55, 131, 234, 361, 824, 5, 81,
    623, 48, 961, 19, 26, 33, 10, 1101, 365, 92, 88, 181, 275, 346, 201, 206, 86, 36, 219, 324,
    829, 840, 64, 326, 19, 48, 122, 85, 216, 284, 919, 861, 326, 985, 233, 64, 68, 232, 431, 960,
    50, 29, 81, 216, 321, 603, 14, 612, 81, 360, 36, 51, 62, 194, 78, 60, 200, 314, 676, 112,
    4, 28, 18, 61, 136, 247, 819, 921, 1060, 464, 895, 10, 6, 66, 119, 38, 41, 49, 602, 423,
    962, 302, 294, 875, 78, 14, 23, 111, 109, 62, 31, 501, 823, 216, 280, 34, 24, 150, 1000, 162,
    286, 19, 21, 17, 340, 19, 242, 31, 86, 234, 140, 607, 115, 33, 191, 67, 104, 86, 52, 88,
    16, 80, 121, 67, 95, 122, 216, 548, 96, 11, 201, 77, 364, 218, 65, 667, 890, 236, 154, 211,
    10, 98, 34, 119, 56, 216, 119, 71, 218, 1164, 1496, 1817, 51, 39, 210, 36, 3, 19, 540, 232,
    22, 141, 617, 84, 290, 80, 46, 207, 411, 150, 29, 38, 46, 172, 85, 194, 39, 261, 543, 897,
    624, 18, 212, 416, 127, 931, 19, 4, 63, 96, 12, 101, 418, 16, 140, 230, 460, 538, 19, 27,
    88, 612, 1431, 90, 716, 275, 74, 83, 11, 426, 89, 72, 84, 1300, 1706, 814, 221, 132, 40, 102,
    34, 868, 975, 1101, 84, 16, 79, 23, 16, 81, 122, 324, 403, 912, 227, 936, 447, 55, 86, 34,
    43, 212, 107, 96, 314, 264, 1065, 323, 428, 601, 203, 124, 95, 216, 814, 2906, 654, 820, 2, 301,
    112, 176, 213, 71, 87, 96, 202, 35, 10, 2, 41, 17, 84, 221, 736, 820, 214, 11, 60, 760,
]

# Beale Cipher 2 (Contents) - 763 numbers, solved via DoI
B2_CIPHER = [
    115, 73, 24, 807, 37, 52, 49, 17, 31, 62, 647, 22, 7, 15, 140, 47, 29, 107, 79, 84,
    56, 239, 10, 26, 811, 5, 196, 308, 85, 52, 160, 136, 59, 211, 36, 9, 46, 316, 554, 122,
    106, 95, 53, 58, 2, 42, 7, 35, 122, 53, 31, 82, 77, 250, 196, 56, 96, 118, 71, 140,
    287, 28, 353, 37, 1005, 65, 147, 807, 24, 3, 8, 12, 47, 43, 59, 807, 45, 316, 101, 41,
    78, 154, 1005, 122, 138, 191, 16, 77, 49, 102, 57, 72, 34, 73, 85, 35, 371, 59, 196, 81,
    92, 191, 106, 273, 60, 394, 620, 270, 220, 106, 388, 287, 63, 3, 6, 191, 122, 43, 234, 400,
    106, 290, 314, 47, 48, 81, 96, 26, 115, 92, 158, 191, 110, 77, 85, 197, 46, 10, 113, 140,
    353, 48, 120, 106, 2, 607, 61, 420, 811, 29, 125, 14, 20, 37, 105, 28, 248, 16, 159, 7,
    35, 19, 301, 125, 110, 486, 287, 98, 117, 511, 62, 51, 220, 37, 113, 140, 807, 138, 540, 8,
    44, 287, 388, 117, 18, 79, 344, 34, 20, 59, 511, 548, 107, 603, 220, 7, 66, 154, 41, 20,
    50, 6, 575, 122, 154, 248, 110, 61, 52, 33, 30, 5, 38, 8, 14, 84, 57, 540, 217, 115,
    71, 29, 84, 63, 43, 131, 29, 138, 47, 73, 239, 540, 52, 53, 79, 118, 51, 44, 63, 196,
    12, 239, 112, 3, 49, 79, 353, 105, 56, 371, 557, 211, 505, 125, 360, 133, 143, 101, 15, 284,
    540, 252, 14, 205, 140, 344, 26, 811, 138, 115, 48, 73, 34, 205, 316, 607, 63, 220, 7, 52,
    150, 44, 52, 16, 40, 37, 158, 807, 37, 121, 12, 95, 10, 15, 35, 12, 131, 62, 115, 102,
    807, 49, 53, 135, 138, 30, 31, 62, 67, 41, 85, 63, 10, 106, 807, 138, 8, 113, 20, 32,
    33, 37, 353, 287, 140, 47, 85, 50, 37, 49, 47, 64, 6, 7, 71, 33, 4, 43, 47, 63,
    1, 27, 600, 208, 230, 15, 191, 246, 85, 94, 511, 2, 270, 20, 39, 7, 33, 44, 22, 40,
    7, 10, 3, 811, 106, 44, 486, 230, 353, 211, 200, 31, 10, 38, 140, 297, 61, 603, 320, 302,
    666, 287, 2, 44, 33, 32, 511, 548, 10, 6, 250, 557, 246, 53, 37, 52, 83, 47, 320, 38,
    33, 807, 7, 44, 30, 31, 250, 10, 15, 35, 106, 160, 113, 31, 102, 406, 230, 540, 320, 29,
    66, 33, 101, 807, 138, 301, 316, 353, 320, 220, 37, 52, 28, 540, 320, 33, 8, 48, 107, 50,
    811, 7, 2, 113, 73, 16, 125, 11, 110, 67, 102, 807, 33, 59, 81, 158, 38, 43, 581, 138,
    19, 85, 400, 38, 43, 77, 14, 27, 8, 47, 138, 63, 140, 44, 35, 22, 177, 106, 250, 314,
    217, 2, 10, 7, 1005, 4, 20, 25, 44, 48, 7, 26, 46, 110, 230, 807, 191, 34, 112, 147,
    44, 110, 121, 125, 96, 41, 51, 50, 140, 56, 47, 152, 540, 63, 807, 28, 42, 250, 138, 582,
    98, 643, 32, 107, 140, 112, 26, 85, 138, 540, 53, 20, 125, 371, 38, 36, 10, 52, 118, 136,
    102, 420, 150, 112, 71, 14, 20, 7, 24, 18, 12, 807, 37, 67, 110, 62, 33, 21, 95, 220,
    511, 102, 811, 30, 83, 84, 305, 620, 15, 2, 10, 8, 220, 106, 353, 105, 106, 60, 275, 72,
    8, 50, 205, 185, 112, 125, 540, 65, 106, 807, 138, 96, 110, 16, 73, 33, 807, 150, 409, 400,
    50, 154, 285, 96, 106, 316, 270, 205, 101, 811, 400, 8, 44, 37, 52, 40, 241, 34, 205, 38,
    16, 46, 47, 85, 24, 44, 15, 64, 73, 138, 807, 85, 78, 110, 33, 420, 505, 53, 37, 38,
    22, 31, 10, 110, 106, 101, 140, 15, 38, 3, 5, 44, 7, 98, 287, 135, 150, 96, 33, 84,
    125, 807, 191, 96, 511, 118, 40, 370, 643, 466, 106, 41, 107, 603, 220, 275, 30, 150, 105, 49,
    53, 287, 250, 208, 134, 7, 53, 12, 47, 85, 63, 138, 110, 21, 112, 140, 485, 486, 505, 14,
    73, 84, 575, 1005, 150, 200, 16, 42, 5, 4, 25, 42, 8, 16, 811, 125, 160, 32, 205, 603,
    807, 81, 96, 405, 41, 600, 136, 14, 20, 28, 26, 353, 302, 246, 8, 131, 160, 140, 84, 440,
    42, 16, 811, 40, 67, 101, 102, 194, 138, 205, 51, 63, 241, 540, 122, 8, 10, 63, 140, 47,
    48, 140, 288,
]

# Beale Cipher 3 (Names) - 618 numbers, unsolved
B3_CIPHER = [
    317, 8, 92, 73, 112, 89, 67, 318, 28, 96, 107, 41, 631, 78, 146, 397, 118, 98, 114, 246,
    348, 116, 74, 88, 12, 65, 32, 14, 81, 19, 76, 121, 216, 85, 33, 66, 15, 108, 68, 77,
    43, 24, 122, 96, 117, 36, 211, 301, 15, 44, 11, 46, 89, 18, 136, 68, 317, 28, 90, 82,
    304, 71, 43, 221, 198, 176, 310, 319, 81, 99, 264, 380, 56, 37, 319, 2, 44, 53, 28, 44,
    75, 98, 102, 37, 85, 107, 117, 64, 88, 136, 48, 151, 99, 175, 89, 315, 326, 78, 96, 214,
    218, 311, 43, 89, 51, 90, 75, 128, 96, 33, 28, 103, 84, 65, 26, 41, 246, 84, 270, 98,
    116, 32, 59, 74, 66, 69, 240, 15, 8, 121, 20, 77, 89, 31, 11, 106, 81, 191, 224, 328,
    18, 75, 52, 82, 117, 201, 39, 23, 217, 27, 21, 84, 35, 54, 109, 128, 49, 77, 88, 1,
    81, 217, 64, 55, 83, 116, 251, 269, 311, 96, 54, 32, 120, 18, 132, 102, 219, 211, 84, 150,
    219, 275, 312, 64, 10, 106, 87, 75, 47, 21, 29, 37, 81, 44, 18, 126, 115, 132, 160, 181,
    203, 76, 81, 299, 314, 337, 351, 96, 11, 28, 97, 318, 238, 106, 24, 93, 3, 19, 17, 26,
    60, 73, 88, 14, 126, 138, 234, 286, 297, 321, 365, 264, 19, 22, 84, 56, 107, 98, 123, 111,
    214, 136, 7, 33, 45, 40, 13, 28, 46, 42, 107, 196, 227, 344, 198, 203, 247, 116, 19, 8,
    212, 230, 31, 6, 328, 65, 48, 52, 59, 41, 122, 33, 117, 11, 18, 25, 71, 36, 45, 83,
    76, 89, 92, 31, 65, 70, 83, 96, 27, 33, 44, 50, 61, 24, 112, 136, 149, 176, 180, 194,
    143, 171, 205, 296, 87, 12, 44, 51, 89, 98, 34, 41, 208, 173, 66, 9, 35, 16, 95, 8,
    113, 175, 90, 56, 203, 19, 177, 183, 206, 157, 200, 218, 260, 291, 305, 618, 951, 320, 18, 124,
    78, 65, 19, 32, 124, 48, 53, 57, 84, 96, 207, 244, 66, 82, 119, 71, 11, 86, 77, 213,
    54, 82, 316, 245, 303, 86, 97, 106, 212, 18, 37, 15, 81, 89, 16, 7, 81, 39, 96, 14,
    43, 216, 118, 29, 55, 109, 136, 172, 213, 64, 8, 227, 304, 611, 221, 364, 819, 375, 128, 296,
    1, 18, 53, 76, 10, 15, 23, 19, 71, 84, 120, 134, 66, 73, 89, 96, 230, 48, 77, 26,
    101, 127, 936, 218, 439, 178, 171, 61, 226, 313, 215, 102, 18, 167, 262, 114, 218, 66, 59, 48,
    27, 19, 13, 82, 48, 162, 119, 34, 127, 139, 34, 128, 129, 74, 63, 120, 11, 54, 61, 73,
    92, 180, 66, 75, 101, 124, 265, 89, 96, 126, 274, 896, 917, 434, 461, 235, 890, 312, 413, 328,
    381, 96, 105, 217, 66, 118, 22, 77, 64, 42, 12, 7, 55, 24, 83, 67, 97, 109, 121, 135,
    181, 203, 219, 228, 256, 21, 34, 77, 319, 374, 382, 675, 684, 717, 864, 203, 4, 18, 92, 16,
    63, 82, 22, 46, 55, 69, 74, 112, 134, 186, 175, 119, 213, 416, 312, 343, 264, 119, 186, 218,
    343, 417, 845, 951, 124, 209, 49, 617, 856, 924, 936, 72, 19, 28, 11, 35, 42, 40, 66, 85,
    94, 112, 65, 82, 115, 119, 236, 244, 186, 172, 112, 85, 6, 56, 38, 44, 85, 72, 32, 47,
    63, 96, 124, 217, 314, 319, 221, 644, 817, 821, 934, 922, 416, 975, 10, 22, 18, 46, 137, 181,
    101, 39, 86, 103, 116, 138, 164, 212, 218, 296, 815, 380, 412, 460, 495, 675, 820, 952,
]

# B2 solved plaintext
B2_PLAINTEXT = """I have deposited in the county of Bedford about four miles from Bufords in an excavation or vault six feet below the surface of the ground the following articles belonging jointly to the parties whose names are given in number three herewith The first deposit consisted of one thousand and fourteen pounds of gold and three thousand eight hundred and twelve pounds of silver deposited November eighteen nineteen The second was made December eighteen twenty one and consisted of nineteen hundred and seven pounds of gold and twelve hundred and eighty eight pounds of silver also jewels obtained in St Louis in exchange for silver to save transportation and valued at thirteen thousand dollars The above is securely packed in iron pots with iron covers The vault is roughly lined with stone and the vessels rest on solid stone and are covered with others Paper number one describes the exact locality of the vault so that no difficulty will be had in finding it"""

# Declaration of Independence (Beale's key text for B2)
DOI_TEXT = """When in the Course of human events, it becomes necessary for one people

to dissolve the political bands which have connected them with another,

and to assume, among the Powers of the earth, the separate and equal

station to which the Laws of Nature and of Nature's God entitle them,

a decent respect to the opinions of mankind requires that they should

declare the causes which impel them to the separation.



We hold these truths to be self-evident, that all men are created

equal, that they are endowed by their Creator with certain inalienable

Rights, that among these are Life, Liberty, and the pursuit of

Happiness. That to secure these rights, Governments are instituted

among Men, deriving their just powers from the consent of the governed,

That whenever any Form of Government becomes destructive of these

ends, it is the Right of the People to alter or to abolish it, and to

institute a new Government, laying its foundation on such principles

and organizing its powers in such form, as to them shall seem most

likely to effect their Safety and Happiness. Prudence, indeed, will

dictate that Governments long established should not be changed for

light and transient causes; and accordingly all experience hath shown,

that mankind are more disposed to suffer, while evils are sufferable,

than to right themselves by abolishing the forms to which they are

accustomed. But when a long train of abuses and usurpations, pursuing

invariably the same Object evinces a design to reduce them under

absolute Despotism, it is their right, it is their duty, to throw off

such Government, and to provide new Guards for their future security.

--Such has been the patient sufferance of these Colonies; and such is

now the necessity which constrains them to alter their former Systems

of Government. The history of the present King of Great Britain is a

history of repeated injuries and usurpations, all having in direct

object the establishment of an absolute Tyranny over these States. To

prove this, let Facts be submitted to a candid world.



He has refused his Assent to Laws, the most wholesome and necessary for

the public good.



He has forbidden his Governors to pass Laws of immediate and pressing

importance, unless suspended in their operation till his Assent should

be obtained; and when so suspended, he has utterly neglected to attend

to them.



He has refused to pass other Laws for the accommodation of large

districts of people, unless those people would relinquish the right

of Representation in the Legislature, a right inestimable to them and

formidable to tyrants only.



He has called together legislative bodies at places unusual,

uncomfortable, and distant from the depository of their Public Records,

for the sole purpose of fatiguing them into compliance with his

measures.



He has dissolved Representative Houses repeatedly, for opposing with

manly firmness his invasions on the rights of the people.



He has refused for a long time, after such dissolutions, to cause

others to be elected; whereby the Legislative Powers, incapable of

Annihilation, have returned to the People at large for their exercise;

the State remaining in the mean time exposed to all the dangers of

invasion from without, and convulsions within.



He has endeavoured to prevent the population of these States; for that

purpose obstructing the Laws of Naturalization of Foreigners; refusing

to pass others to encourage their migration hither, and raising the

conditions of new Appropriations of Lands.



He has obstructed the Administration of Justice, by refusing his Assent

to Laws for establishing Judiciary Powers.



He has made judges dependent on his Will alone, for the tenure of their

offices, and the amount and payment of their salaries.



He has erected a multitude of New Offices, and sent hither swarms of

Officers to harass our People, and eat out their substance.



He has kept among us, in times of peace, Standing Armies without the

Consent of our legislatures.



He has affected to render the Military independent of and superior to

the Civil Power.



He has combined with others to subject us to a jurisdiction foreign to

our constitution, and unacknowledged by our laws; giving his Assent to

their Acts of pretended legislation:



For quartering large bodies of armed troops among us:



For protecting them, by a mock Trial, from Punishment for any Murders

which they should commit on the Inhabitants of these States:



For cutting off our Trade with all parts of the world:



For imposing taxes on us without our Consent:



For depriving us, in many cases, of the benefits of Trial by Jury:



For transporting us beyond Seas to be tried for pretended offences:



For abolishing the free System of English Laws in a neighbouring

Province, establishing therein an Arbitrary government, and enlarging

its Boundaries so as to render it at once an example and fit instrument

for introducing the same absolute rule into these Colonies:



For taking away our Charters, abolishing our most valuable Laws, and

altering fundamentally the Forms of our Governments:



For suspending our own Legislatures, and declaring themselves invested

with Power to legislate for us in all cases whatsoever.



He has abdicated Government here, by declaring us out of his Protection

and waging War against us.



He has plundered our seas, ravaged our Coasts, burnt our towns, and

destroyed the lives of our people.



He is at this time transporting large armies of foreign mercenaries

to compleat the works of death, desolation and tyranny, already begun

with circumstances of Cruelty & perfidy scarcely paralleled in the most

barbarous ages, and totally unworthy of the Head of a civilized nation.



He has constrained our fellow Citizens taken Captive on the high Seas

to bear Arms against their Country, to become the executioners of their

friends and Brethren, or to fall themselves by their Hands.



He has excited domestic insurrections amongst us, and has endeavoured

to bring on the inhabitants of our frontiers, the merciless Indian

Savages, whose known rule of warfare, is an undistinguished destruction

of all ages, sexes and conditions.



In every stage of these Oppressions We have Petitioned for Redress in

the most humble terms: Our repeated Petitions have been answered only

by repeated injury. A Prince, whose character is thus marked by every

act which may define a Tyrant, is unfit to be the ruler of a free

People.



Nor have We been wanting in attention to our British brethren. We have

warned them from time to time of attempts by their legislature to

extend an unwarrantable jurisdiction over us. We have reminded them

of the circumstances of our emigration and settlement here. We have

appealed to their native justice and magnanimity, and we have conjured

them by the ties of our common kindred to disavow these usurpations,

which would inevitably interrupt our connections and correspondence.

They too have been deaf to the voice of justice and of consanguinity.

We must, therefore, acquiesce in the necessity, which denounces our

Separation, and hold them, as we hold the rest of mankind, Enemies in

War, in Peace Friends.



We, therefore, the Representatives of the United States of America,

in General Congress, Assembled, appealing to the Supreme Judge of the

world for the rectitude of our intentions, do, in the Name, and by the

Authority of the good People of these Colonies, solemnly publish and

declare, That these United Colonies are, and of Right ought to be Free

and Independent States; that they are Absolved from all Allegiance to

the British Crown, and that all political connection between them and

the State of Great Britain, is and ought to be totally dissolved; and

that as Free and Independent States, they have full Power to levy War,

conclude Peace, contract Alliances, establish Commerce, and to do all

other Acts and Things which Independent States may of right do. And for

the support of this Declaration, with a firm reliance on the Protection

of Divine Providence, we mutually pledge to each other our Lives, our

Fortunes and our sacred Honor"""

# DoI split into individual words
DOI_WORDS = re.findall(r"[A-Za-z']+", DOI_TEXT)

# English letter frequencies (percentages)
ENGLISH_FREQ = {
    'A': 8.167,
    'B': 1.492,
    'C': 2.782,
    'D': 4.253,
    'E': 12.702,
    'F': 2.228,
    'G': 2.015,
    'H': 6.094,
    'I': 6.966,
    'J': 0.153,
    'K': 0.772,
    'L': 4.025,
    'M': 2.406,
    'N': 6.749,
    'O': 7.507,
    'P': 1.929,
    'Q': 0.095,
    'R': 5.987,
    'S': 6.327,
    'T': 9.056,
    'U': 2.758,
    'V': 0.978,
    'W': 2.36,
    'X': 0.15,
    'Y': 1.974,
    'Z': 0.074,
}

# Common English bigrams
COMMON_BIGRAMS = {
    'AL', 'AN', 'AR', 'AS', 'AT', 'CO', 'DE', 'EA', 'ED', 'EN',
    'ER', 'ES', 'HA', 'HE', 'HI', 'IC', 'IN', 'IO', 'IS', 'IT',
    'LE', 'ME', 'ND', 'NE', 'NG', 'NT', 'OF', 'ON', 'OR', 'OU',
    'RE', 'RI', 'RO', 'SE', 'ST', 'TE', 'TH', 'TI', 'TO', 'VE',
}

# Common English trigrams
COMMON_TRIGRAMS = {
    'ALL', 'AND', 'ENT', 'ERE', 'FOR', 'HAT', 'HER', 'HIS', 'ING', 'ION',
    'ITH', 'TER', 'THA', 'THE', 'THI', 'TIO', 'VER', 'WAS', 'WIT', 'YOU',
}

# Common English words
COMMON_WORDS = {
    'ABOUT', 'AFTER', 'ALL', 'AND', 'ARE', 'BEEN', 'BUT', 'CAN', 'COULD', 'DID',
    'EACH', 'FOR', 'FROM', 'GET', 'HAD', 'HAS', 'HAVE', 'HER', 'HIM', 'HIS',
    'HOW', 'ITS', 'LET', 'MAY', 'NEW', 'NOT', 'NOW', 'OLD', 'ONE', 'OTHER',
    'OUR', 'OUT', 'SAID', 'SAY', 'SEE', 'SHE', 'THAT', 'THE', 'THEIR', 'THERE',
    'THESE', 'THEY', 'THIS', 'THOSE', 'TOO', 'USE', 'WAS', 'WAY', 'WHICH', 'WHO',
    'WILL', 'WITH', 'WOULD', 'YOU', 'YOUR',
}

# Gillogly sequence (1980) - alphabetical run in B1 via DoI key
GILLOGLY_POSITIONS = {
    'start': 190,
    'end': 203,
    'sequence': 'DEFGHIIJKLMMNO',
    'cipher': 'B1',
    'probability': 1e-12,
}

# Beale DoI offset: cipher_number -> offset from standard DOI_WORDS
# Reconstructed by aligning B2 decode against known B2 plaintext.
# Usage: doi_idx = cipher_number - 1 + BEALE_DOI_OFFSET.get(cipher_number, 0)
BEALE_DOI_OFFSET = {
    1: 0,
    2: 0,
    3: 0,
    4: 0,
    5: 0,
    6: 0,
    7: 0,
    8: 0,
    9: 0,
    10: 0,
    11: 0,
    12: 0,
    14: 0,
    15: 0,
    16: 0,
    17: 0,
    18: 0,
    19: 0,
    20: 0,
    21: 0,
    22: 0,
    24: 0,
    25: 0,
    26: 0,
    27: 0,
    28: 0,
    29: 0,
    30: 0,
    31: 0,
    32: 0,
    33: 0,
    34: 0,
    35: 0,
    36: 0,
    37: 0,
    38: 0,
    39: 0,
    40: 0,
    41: 0,
    42: 0,
    43: 0,
    44: 0,
    45: 0,
    46: 0,
    47: 0,
    48: 0,
    49: 0,
    50: 0,
    51: 0,
    52: 0,
    53: 0,
    56: 0,
    57: 0,
    58: 0,
    59: 0,
    60: 0,
    61: 0,
    62: 0,
    63: 0,
    64: 0,
    65: 0,
    66: 0,
    67: 0,
    71: 0,
    72: 0,
    73: 0,
    77: 0,
    78: 0,
    79: 0,
    81: 0,
    82: 0,
    83: 0,
    84: 0,
    85: 0,
    92: 0,
    94: 0,
    95: 0,
    96: 0,
    98: 0,
    101: 0,
    102: 0,
    105: 0,
    106: 0,
    107: 0,
    110: 0,
    112: 0,
    113: 0,
    115: 0,
    117: 0,
    118: 0,
    120: 0,
    121: 0,
    122: 0,
    125: 0,
    131: 0,
    133: 0,
    134: 0,
    135: 0,
    136: 0,
    138: 0,
    140: 0,
    143: 0,
    147: 0,
    150: 0,
    152: 0,
    154: 0,
    158: 0,
    159: 0,
    160: 0,
    177: 0,
    185: 0,
    191: 0,
    194: 0,
    196: 0,
    197: 0,
    200: 0,
    205: 0,
    208: 0,
    211: 0,
    217: 0,
    220: 0,
    230: 0,
    234: 0,
    239: 0,
    241: 0,
    246: 1,
    248: 1,
    250: 1,
    252: 1,
    270: 1,
    273: 1,
    275: 0,
    284: 1,
    285: 1,
    287: 1,
    288: 1,
    290: 1,
    297: 1,
    301: 1,
    302: 1,
    305: 1,
    308: 1,
    314: 1,
    316: 1,
    320: 1,
    344: 1,
    353: 1,
    360: 1,
    370: 1,
    371: 1,
    388: 1,
    394: 1,
    400: 1,
    405: 1,
    406: 1,
    409: 1,
    420: 1,
    440: 0,
    466: 1,
    485: 11,
    486: 11,
    505: 11,
    511: 3,
    540: 11,
    548: 11,
    554: 1,
    557: -6,
    575: 11,
    581: -3,
    582: 11,
    600: 11,
    603: 11,
    607: 11,
    620: -6,
    643: -2,
    647: -7,
    666: 12,
    807: 13,
    811: 0,
    1005: 0,
}

def beale_decode(cipher, doi_words=None, use_beale_offset=True):
    """Decode a cipher using DoI book cipher, optionally with Beale offset correction."""
    words = doi_words or DOI_WORDS
    decoded = []
    for num in cipher:
        off = BEALE_DOI_OFFSET.get(num, 0) if use_beale_offset else 0
        idx = num - 1 + off
        if 0 <= idx < len(words):
            decoded.append(words[idx][0].upper())
        else:
            decoded.append('?')
    return ''.join(decoded)
