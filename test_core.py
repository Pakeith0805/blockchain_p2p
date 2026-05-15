from core import Blockchain

def main():
    print("--- 1. 初期化とジェネシスブロックの生成 ---")
    # 難易度4でブロックチェーンを初期化
    my_blockchain = Blockchain(difficulty=4)
    print("Genesis block created.\n")

    print("--- 2. 新しいブロックの追加（マイニング） ---")
    print("Adding Block 1...")
    my_blockchain.add_block("Alice sends 5 coins to Bob")
    print("Block 1 added.\n")

    print("Adding Block 2...")
    my_blockchain.add_block("Bob sends 2 coins to Charlie")
    print("Block 2 added.\n")

    print("--- 3. ブロックチェーンの正当性検証 ---")
    is_valid = my_blockchain.is_valid()
    print(f"チェーンは有効か？: {is_valid}\n")

    print("--- 4. 改ざん検知テスト ---")
    print("Block 1 のトランザクションを改ざんします...")
    my_blockchain.chain[1].transaction = "Alice sends 10000 coins to Bob" # 改ざん
    
    is_valid_after_tamper = my_blockchain.is_valid()
    print(f"改ざん後のチェーンは有効か？: {is_valid_after_tamper}")

if __name__ == "__main__":
    main()
