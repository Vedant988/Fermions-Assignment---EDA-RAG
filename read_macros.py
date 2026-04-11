import sys
with open(sys.argv[1]) as f:
    text = f.read()
    idx = text.find('#define TEST_RR_OP')
    if idx != -1:
        print(text[idx:idx+400])
